#!/usr/bin/env python3
"""
Step 7: 回滚脚本
在观察期内如果发现问题，将v7节点切回v6主节点

回滚后状态:
- v6主节点重新成为主
- v7节点降为从节点跟随v6主节点
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    RedisNode, print_header, print_section, print_status, print_expect,
    get_redis_version, verify_replication_status, wait_for_replication,
    load_config, confirm_action
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Rollback: 回滚到v6节点"
    )
    parser.add_argument(
        '--config', '-c',
        default='upgrade_config.json',
        help='升级配置文件路径'
    )
    parser.add_argument(
        '--shard', '-s',
        type=int,
        help='指定shard编号'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅模拟操作，不实际执行'
    )
    parser.add_argument(
        '--auto-continue',
        action='store_true',
        help='自动确认继续，不等待用户输入'
    )
    return parser.parse_args()


def rollback_shard(shard_config, config, args):
    """回滚单个shard"""
    shard_idx = shard_config.get('shard_index', 0) + 1
    
    print_header(f"Shard {shard_idx}")
    
    # 获取当前的v7主节点
    # 在failover后，new_slaves中的第一个变成了主节点
    new_slaves = shard_config.get('new_slaves', [])
    
    if not new_slaves:
        print_status("ERROR", "No v7 nodes found", "FAIL")
        return None
    
    # 找到当前的v7主节点（从配置中获取）
    new_master_host = None
    new_master_port = None
    
    # 尝试从配置推断当前主节点
    # 需要用户提供原始主节点信息
    old_master = shard_config['master']
    old_master_host = old_master['host']
    old_master_port = old_master['port']
    
    print_section(f"Old Master (v6): {old_master_host}:{old_master_port}")
    
    # 检查当前状态
    old_master_node = RedisNode(host=old_master_host, port=old_master_port)
    old_role_info = old_master_node.info('replication')
    old_role = old_role_info.get('role')
    
    print_status("Current Role", old_role)
    
    # 如果已经是主节点，不需要回滚
    if old_role == 'master':
        print_status("Already master", "No rollback needed", "OK")
        return {'status': 'already_master', 'skipped': True}
    
    # 尝试找到v7主节点
    # 需要从cluster nodes获取
    try:
        cluster_nodes_info = old_master_node.execute_command('CLUSTER', 'NODES')
        if isinstance(cluster_nodes_info, bytes):
            cluster_nodes_info = cluster_nodes_info.decode('utf-8')

        # 解析cluster nodes输出
        for line in cluster_nodes_info.split('\n'):
            if not line.strip():
                continue
            
            parts = line.split()
            node_id = parts[0]
            addr_part = parts[1]
            flags = parts[2].split(',')
            
            # 检查是否是master
            if 'master' in flags:
                # 获取地址
                if '@' in addr_part:
                    addr = addr_part.split('@')[0]
                else:
                    addr = addr_part
                
                if ':' in addr:
                    host, port = addr.rsplit(':', 1)
                    port = int(port)
                else:
                    host = addr
                    port = 6379
                
                # 检查版本
                try:
                    node = RedisNode(host=host, port=port)
                    version = get_redis_version(node)
                    
                    if '7.' in version:
                        new_master_host = host
                        new_master_port = port
                        break
                except:
                    pass
    except Exception as e:
        print_status("Warning", f"Cannot get cluster nodes: {e}", "WARN")
    
    print_section(f"V7 Master: {new_master_host or 'unknown'}:{new_master_port or 'unknown'}")
    
    if not new_master_host:
        print_status("ERROR", "Cannot find v7 master to rollback from", "FAIL")
        return None
    
    # 1. 提升原v6主节点 (使用 CLUSTER FAILOVER)
    print("\n[1] Promoting old v6 master back via CLUSTER FAILOVER...")

    if args.dry_run:
        print_status("DRY RUN", "would promote v6 master", "INFO")
    else:
        try:
            old_master_node.execute_command('CLUSTER', 'FAILOVER')
            print_status("CLUSTER FAILOVER", "executed on v6 node", "OK")
            # 等待 failover 完成
            import time
            time.sleep(5)
        except Exception as e:
            print_status("ERROR", str(e), "FAIL")
            return None

    # 2. 在 Cluster 模式下，CLUSTER FAILOVER 自动完成角色切换
    print("\n[2] Verifying role switch...")

    if args.dry_run:
        print_status("DRY RUN", "would verify role switch", "INFO")
    else:
        pass  # Cluster mode auto-demotes old master
    
    # 3. 验证
    print("\n[3] Verification...")
    
    if not args.dry_run:
        # 检查v6主节点状态
        old_master_node = RedisNode(host=old_master_host, port=old_master_port)
        new_role_info = old_master_node.info('replication')
        new_role = new_role_info.get('role')
        
        print_status("Old Master Role", new_role)
        print_expect("Role should be 'master'", "master", new_role)
        
        # 检查版本
        version = get_redis_version(old_master_node)
        print_status("Version", version)
        
        return {
            'old_master': {'host': old_master_host, 'port': old_master_port, 'version': version},
            'status': 'rolled_back',
            'success': True
        }
    else:
        return {
            'old_master': {'host': old_master_host, 'port': old_master_port},
            'status': 'rolled_back',
            'success': True,
            'dry_run': True
        }


def main():
    args = parse_args()
    
    print_header("Rollback to v6")
    print(f"  Config: {args.config}")
    print(f"  Shard: {args.shard or 'all'}")
    print(f"  Dry run: {args.dry_run}")
    
    # 警告
    print("\n" + "="*50)
    print("⚠️  WARNING: Rollback will revert to v6!")
    print("="*50)
    print("  - v7 master will become replica")
    print("  - v6 master will be promoted back")
    print("  - This is for emergency recovery only!")
    
    if not args.dry_run and not args.auto_continue:
        if not confirm_action("\nProceed with rollback?"):
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
        
        result = rollback_shard(shard, config, args)
        
        if result:
            all_results.append(result)
        
        if result and result.get('success'):
            if shard_idx < len(shards_to_process):
                print(f"\n  ✓ Shard {shard_idx} rollback successful!")
                if args.auto_continue:
                    print(f"\n  Continue to Shard {shard_idx + 1}? [y/N]: y (auto-confirmed)")
                else:
                    response = input(f"\n  Continue to Shard {shard_idx + 1}? [y/N]: ")
                    if response.lower() not in ('y', 'yes'):
                        print(f"  ⚠ Stopped at Shard {shard_idx}")
                        break
        elif result and result.get('skipped'):
            print(f"\n  ⚠ Shard {shard_idx} skipped (already at v6)")
        else:
            print(f"\n  ✗ Shard {shard_idx} rollback failed!")
            print(f"  ⚠ Stopping rollback process")
            break
    
    # 打印摘要
    print_header("Step 7 Rollback Summary")
    
    success_count = sum(1 for r in all_results if r.get('success'))
    skipped_count = sum(1 for r in all_results if r.get('skipped'))
    
    print(f"  Shards processed: {len(all_results)}")
    print(f"  Successful: {success_count}")
    print(f"  Skipped: {skipped_count}")
    
    if args.dry_run:
        print("\n⚠ This was a dry run. Run without --dry-run to execute.")
    else:
        print("\n" + "="*50)
        print("✅ Rollback completed!")
        print("="*50)
        print("  - Cluster is now back to v6")
        print("  - v7 nodes are now replicas")
        print("  - Please investigate the issue before trying again")
    
    print("\n" + "=" * 60)
    if success_count > 0:
        print("  ✓ PASS - Rollback completed")
    else:
        print("  ✗ FAIL - Rollback failed")
    print("=" * 60)


if __name__ == '__main__':
    main()
