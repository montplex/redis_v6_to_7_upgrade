#!/usr/bin/env python3
"""
Step 6 / Step 10: Failover到v7节点脚本
将v7从节点提升为主节点

使用场景:
- Step 6: 首次Failover到v7
- Step 10: 重新Failover到v7 (回滚后)

支持两种模式:
- Standalone模式: 使用 REPLICAOF NO ONE 命令
- Cluster模式: 使用 CLUSTER FAILOVER 命令
"""

import sys
import os
import argparse
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    RedisNode, print_header, print_section, print_status, print_expect,
    get_redis_version, verify_replication_status, wait_for_replication,
    load_config, save_config, confirm_action
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Step 6: Failover to v7 - 切换到v7节点作为主节点"
    )
    parser.add_argument(
        '--config', '-c',
        default='upgrade_config.json',
        help='升级配置文件路径'
    )
    parser.add_argument(
        '--shard', '-s',
        type=int,
        help='指定shard编号 (从1开始)'
    )
    parser.add_argument(
        '--replica-index', '-r',
        type=int,
        default=1,
        help='选择第几个v7从节点作为新主 (default: 1)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅模拟操作，不实际执行'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=60,
        help='等待复制追平的超时时间(秒)'
    )
    parser.add_argument(
        '--auto-continue',
        action='store_true',
        help='自动确认继续，不等待用户输入'
    )
    return parser.parse_args()


def failover_shard(shard_config, config, args):
    """对单个shard执行failover"""
    shard_idx = shard_config.get('shard_index', 0) + 1
    
    print_header(f"Shard {shard_idx}")
    
    # 获取主节点
    master = shard_config['master']
    old_master_host = master['host']
    old_master_port = master['port']
    master_password = config.get('master_password', '')
    
    print_section(f"Old Master: {old_master_host}:{old_master_port}")
    
    # 获取v7从节点
    new_slaves = shard_config.get('new_slaves', [])
    
    if not new_slaves or len(new_slaves) < args.replica_index:
        print_status("ERROR", f"Not enough v7 replicas, need {args.replica_index}", "FAIL")
        return None
    
    # 选择要提升的v7节点
    new_master = new_slaves[args.replica_index - 1]
    new_master_host = new_master.get('host')
    new_master_port = new_master.get('port', 6379)
    new_master_password = new_master.get('password', '')
    
    if not new_master_host:
        print_status("ERROR", f"v7 replica {args.replica_index} not configured", "FAIL")
        return None
    
    print_section(f"New Master (v7): {new_master_host}:{new_master_port}")
    
    # 1. 提升v7从节点为主节点 (Cluster模式: 使用 CLUSTER FAILOVER)
    print("\n[1] Promoting v7 replica to master...")
    
    if args.dry_run:
        print_status("DRY RUN", "would promote v7 replica", "INFO")
    else:
        v7_node = RedisNode(host=new_master_host, port=new_master_port, password=new_master_password)
        
        try:
            # Cluster模式: 使用 CLUSTER FAILOVER
            v7_node.execute_command('CLUSTER', 'FAILOVER')
            print_status("CLUSTER FAILOVER", "executed", "OK")
        except Exception as e:
            print_status("ERROR", str(e), "FAIL")
            return None
    
    # 等待一下让failover完成
    time.sleep(2)
    
    # 2. 原主降为从节点 (Cluster模式下自动完成)
    print("\n[2] Demoting old master to replica...")
    print("  (In cluster mode, CLUSTER FAILOVER automatically demotes old master)")
    
    # 获取新主节点的 node ID（用于 CLUSTER REPLICATE）
    new_master_node_id = None
    try:
        v7_master = RedisNode(host=new_master_host, port=new_master_port, password=new_master_password)
        nodes_info = v7_master.execute_command('CLUSTER', 'NODES')
        if isinstance(nodes_info, bytes):
            nodes_info = nodes_info.decode('utf-8')
        for line in nodes_info.split('\n'):
            if 'myself' in line and 'master' in line:
                new_master_node_id = line.split()[0]
                break
    except Exception as e:
        print_status("Get new master node ID", str(e), "WARN")

    # 3. 其他v7从节点重新挂载到新主
    print("\n[3] Reconfiguring other v7 replicas...")

    if args.dry_run:
        print_status("DRY RUN", "would reconfigure other replicas", "INFO")
    else:
        for idx, slave in enumerate(new_slaves):
            if idx == args.replica_index - 1:
                continue  # 跳过新主节点

            slave_host = slave.get('host')
            slave_port = slave.get('port', 6379)
            slave_password = slave.get('password', '')

            if slave_host:
                print(f"  - Reconfiguring {slave_host}:{slave_port}...")
                slave_node = RedisNode(host=slave_host, port=slave_port, password=slave_password)

                try:
                    if new_master_node_id:
                        slave_node.execute_command('CLUSTER', 'REPLICATE', new_master_node_id)
                        print_status("CLUSTER REPLICATE", "done", "OK")
                    else:
                        print_status("SKIP", "no master node ID", "WARN")
                except Exception as e:
                    # In cluster mode, replicas auto-follow after CLUSTER FAILOVER
                    print_status("INFO", f"auto-follows via gossip ({e})", "WARN")

    # 4. v6从节点重新挂载（可选）
    print("\n[4] Keeping v6 replicas as replicas of new master...")

    if args.dry_run:
        print_status("DRY RUN", "would keep v6 replicas", "INFO")
    else:
        v6_slaves = shard_config.get('slaves', [])

        for slave in v6_slaves:
            slave_host = slave['host']
            slave_port = slave['port']

            print(f"  - {slave_host}:{slave_port} (v6)")
            slave_node = RedisNode(host=slave_host, port=slave_port)

            try:
                if new_master_node_id:
                    slave_node.execute_command('CLUSTER', 'REPLICATE', new_master_node_id)
                    print_status("CLUSTER REPLICATE", "done", "OK")
                else:
                    print_status("SKIP", "no master node ID", "WARN")
            except Exception as e:
                # In cluster mode, replicas auto-follow after CLUSTER FAILOVER
                print_status("INFO", f"auto-follows via gossip ({e})", "WARN")
    
    # 5. 等待复制追平
    print("\n[5] Waiting for replication to catch up...")
    
    if not args.dry_run:
        new_master_node = RedisNode(host=new_master_host, port=new_master_port, password=new_master_password)
        
        # 检查所有从节点
        for slave in new_slaves:
            slave_host = slave.get('host')
            slave_port = slave.get('port', 6379)
            
            if slave_host and slave_host != new_master_host:
                slave_node = RedisNode(host=slave_host, port=slave_port, password=slave_password.get('password', ''))
                
                if wait_for_replication(new_master_node, slave_node, timeout=args.timeout):
                    print_status(f"{slave_host}:{slave_port}", "synced", "OK")
                else:
                    print_status(f"{slave_host}:{slave_port}", "NOT synced", "WARN")
    
    # 验证结果
    print("\n[6] Verification...")
    
    if not args.dry_run:
        # 检查新主状态
        new_master_node = RedisNode(host=new_master_host, port=new_master_port, password=new_master_password)
        new_master_info = new_master_node.info('replication')
        new_master_role = new_master_info.get('role')
        
        print_status("New Master Role", new_master_role)
        print_expect("Role should be 'master'", "master", new_master_role)
        
        if new_master_role != 'master':
            print_status("ERROR", "Promotion failed!", "FAIL")
            return None
        
        # 检查原主降级
        old_master_node = RedisNode(host=old_master_host, port=old_master_port, password=master_password)
        old_master_info = old_master_node.info('replication')
        old_master_role = old_master_info.get('role')
        
        print_status("Old Master Role", old_master_role)
        print_expect("Role should be 'slave'", "slave", old_master_role)
        
        # 检查版本
        old_master_version = get_redis_version(old_master_node)
        new_master_version = get_redis_version(new_master_node)
        
        print_status("Old Master Version", old_master_version)
        print_status("New Master Version", new_master_version)
        
        # Step 6.5: 调整新 v7 master 的复制缓冲区
        print("\n[7] Adjusting replication buffers on new v7 master...")
        try:
            new_master_node.execute_command('CONFIG', 'SET', 'repl-backlog-size', '256mb')
            new_master_node.execute_command('CONFIG', 'SET', 'client-output-buffer-limit', 'slave 512mb 64mb 60')
            new_master_node.execute_command('CONFIG', 'REWRITE')
            print_status("Buffer adjustment", "256mb backlog + 512mb output-buffer", "OK")
        except Exception as e:
            print_status("Buffer adjustment", str(e), "WARN")
        
        return {
            'old_master': {
                'host': old_master_host,
                'port': old_master_port,
                'version': old_master_version,
                'role': old_master_role
            },
            'new_master': {
                'host': new_master_host,
                'port': new_master_port,
                'version': new_master_version,
                'role': new_master_role
            },
            'success': True
        }
    else:
        return {
            'old_master': {'host': old_master_host, 'port': old_master_port},
            'new_master': {'host': new_master_host, 'port': new_master_port},
            'success': True,
            'dry_run': True
        }


def check_shard_failover_status(shard_config, config):
    """检查shard是否已经完成failover
    
    Returns:
        dict: {'already_failover': bool, 'current_master_version': str}
    """
    master = shard_config.get('master', {})
    master_host = master.get('host')
    master_port = master.get('port', 6379)
    master_password = config.get('master_password', '')
    
    if not master_host:
        return {'already_failover': False, 'current_master_version': None}
    
    try:
        master_node = RedisNode(host=master_host, port=master_port, password=master_password)
        master_info = master_node.info('replication')
        master_role = master_info.get('role')
        
        if master_role != 'master':
            return {'already_failover': True, 'current_master_version': 'unknown (now slave)'}
        
        master_version = get_redis_version(master_node)
        
        if master_version.startswith('7.'):
            return {'already_failover': True, 'current_master_version': master_version}
        else:
            return {'already_failover': False, 'current_master_version': master_version}
    except Exception as e:
        return {'already_failover': False, 'error': str(e)}


def main():
    args = parse_args()
    
    print_header("Step 6: Failover to v7")
    print(f"  Config: {args.config}")
    print(f"  Shard: {args.shard or 'all'}")
    print(f"  Replica index: {args.replica_index}")
    print(f"  Dry run: {args.dry_run}")
    
    # 警告
    print("\n" + "="*50)
    print("⚠️  WARNING: This will cause a brief service interruption!")
    print("="*50)
    print("  - The v7 replica will be promoted to master")
    print("  - The old v6 master will become a replica")
    print("  - Client connections will be briefly affected")
    print("  - Consider doing this during low-traffic period")
    
    if not args.dry_run:
        if not confirm_action("\nProceed with failover?", args.auto_continue):
            print("Aborted.")
            sys.exit(1)
    
    # 加载配置
    config = load_config(args.config)
    if not config:
        print_status("ERROR", f"Cannot load config from {args.config}", "FAIL")
        sys.exit(1)
    
    shards = config.get('shards', [])
    
    if not shards:
        print_status("ERROR", "No shards found in config", "FAIL")
        sys.exit(1)
    
    # 选择要处理的shard
    if args.shard:
        if args.shard < 1 or args.shard > len(shards):
            print_status("ERROR", f"Invalid shard number: {args.shard}", "FAIL")
            sys.exit(1)
        shards_to_process = [shards[args.shard - 1]]
    else:
        shards_to_process = shards
    
    print(f"  Processing {len(shards_to_process)} shard(s) sequentially")
    
    all_results = []
    
    for idx, shard in enumerate(shards_to_process):
        shard_idx = idx + 1
        print(f"\n{'='*60}")
        print(f"  Processing Shard {shard_idx}/{len(shards_to_process)}")
        print(f"{'='*60}")
        
        status = check_shard_failover_status(shard, config)
        
        if status.get('already_failover'):
            print(f"\n  ⚠ Shard {shard_idx} already failover!")
            print(f"  Current master version: {status.get('current_master_version')}")
            print(f"  Skipping this shard...")
            continue
        
        result = failover_shard(shard, config, args)
        
        if result:
            all_results.append(result)
        
        if result and result.get('success'):
            if shard_idx < len(shards_to_process):
                print(f"\n  ✓ Shard {shard_idx} failover successful!")
                if args.auto_continue:
                    print(f"\n  Continue to Shard {shard_idx + 1}? [y/N]: y (auto-confirmed)")
                    continue
                response = input(f"\n  Continue to Shard {shard_idx + 1}? [y/N]: ")
                if response.lower() not in ('y', 'yes'):
                    print(f"  ⚠ Stopped at Shard {shard_idx}")
                    break
        else:
            print(f"\n  ✗ Shard {shard_idx} failover failed!")
            print(f"  ⚠ Stopping failover process")
            break
    
    # 打印摘要
    print_header("Step 6 Summary")
    
    success_count = sum(1 for r in all_results if r.get('success'))
    
    print(f"  Shards processed: {len(all_results)}")
    print(f"  Successful: {success_count}")
    
    if args.dry_run:
        print("\n⚠ This was a dry run. Run without --dry-run to execute.")
    else:
        print("\n" + "="*50)
        print("⚠️  IMPORTANT: OBSERVATION PERIOD STARTED!")
        print("="*50)
        print("  - Keep v6 nodes as replicas (DO NOT remove)")
        print("  - Monitor for 1-2 hours (max 4 hours)")
        print("  - If issues found, run rollback.py to revert")
        print("  - After observation period, run remove_v6_nodes.py")
        print("  ⚠️  Note: Do NOT extend to 24-72 hours!")
        print("         Longer mixed-version increases v6 full sync risk")
        
        print_section("Next Steps")
        print("  1. Monitor the cluster for 1-2 hours (max 4 hours)")
        print("  2. Run verify_replication.py periodically to check status")
        print("  3. If OK after observation, run remove_v6_nodes.py")
        print("  4. If issues, run rollback.py")
    
    print("\n" + "=" * 60)
    if success_count == len(shards_to_process):
        print("  ✓ PASS - Failover completed successfully")
    else:
        print(f"  ✗ FAIL - {len(shards_to_process) - success_count} shard(s) failed")
    print("=" * 60)


if __name__ == '__main__':
    main()
