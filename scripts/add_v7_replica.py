#!/usr/bin/env python3
"""
Step 3: 新增v7从节点脚本
为每个shard添加3个v7.2从节点（完整复制原拓扑）

仅支持Cluster模式: 使用 CLUSTER MEET + CLUSTER REPLICATE 命令
"""

import sys
import os
import argparse
import subprocess
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    RedisNode, print_header, print_section, print_status, print_expect,
    get_redis_version, wait_for_replication, verify_replication_status,
    load_config, save_config, confirm_action
)

V7_BINARY = "/home/kerry/test_tmp/v6_to_7/upgrade/bin/redis-server-v7"


def start_v7_node(port):
    """启动v7 Redis节点"""
    dir_path = f"/tmp/redis_v7_{port}"
    # 清除旧数据，避免残留 nodes.conf 导致 "not empty" 错误
    if os.path.exists(dir_path):
        import shutil
        shutil.rmtree(dir_path)
    os.makedirs(dir_path, exist_ok=True)
    
    conf_content = f"""
port {port}
cluster-enabled yes
cluster-config-file {dir_path}/nodes.conf
cluster-node-timeout 5000
appendonly no
daemonize yes
loglevel notice
logfile {dir_path}/redis.log
dir {dir_path}
bind 127.0.0.1
protected-mode no
"""
    
    conf_file = f"{dir_path}/redis.conf"
    with open(conf_file, 'w') as f:
        f.write(conf_content)
    
    try:
        subprocess.run([V7_BINARY, conf_file], capture_output=True, timeout=10)
        time.sleep(1)
        
        node = RedisNode(host='127.0.0.1', port=port)
        if node.ping():
            return True
    except Exception as e:
        print(f"  Failed to start v7 node on port {port}: {e}")
    
    return False


def parse_args():
    parser = argparse.ArgumentParser(
        description="Step 3: Add v7 Replicas - 为每个shard添加3个v7从节点"
    )
    parser.add_argument(
        '--config', '-c',
        default='upgrade_config.json',
        help='升级配置文件路径'
    )
    parser.add_argument(
        '--shard', '-s',
        type=int,
        help='指定shard编号 (从1开始)，不指定则处理所有shard'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅模拟操作，不实际执行'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=120,
        help='等待复制追平的超时时间(秒)'
    )
    return parser.parse_args()


def add_v7_replica(master_host, master_port, master_password,
                   new_host, new_port, new_password,
                   cluster_nodes, timeout=120):
    """添加v7从节点 (Cluster模式)"""
    
    print_section(f"Adding v7 replica (cluster): {new_host}:{new_port}")
    
    # 0. 检查并启动v7节点
    test_node = RedisNode(host=new_host, port=new_port, password=new_password)
    if not test_node.ping():
        print(f"  Starting v7 node on port {new_port}...")
        if not start_v7_node(new_port):
            print_status("Start v7 node", "failed", "FAIL")
            return False
        print_status("Start v7 node", "started", "OK")
    
    new_node = RedisNode(host=new_host, port=new_port, password=new_password)
    
    # 1. 获取master node id
    master_node = RedisNode(host=master_host, port=master_port, password=master_password)
    try:
        result = master_node.execute_command('CLUSTER', 'NODES')
        if isinstance(result, bytes):
            result = result.decode('utf-8')
        for line in result.split('\n'):
            if f':{master_port}@' in line and 'master' in line:
                master_node_id = line.split()[0]
                break
        else:
            # 如果没找到，尝试从第一行获取
            master_node_id = result.split('\n')[0].split()[0]
        print_status("Master Node ID", master_node_id[:8] + "...", "OK")
    except Exception as e:
        print_status("Get master node ID", str(e), "FAIL")
        return False
    
    # 2. 设置replication buffer (仅设置 output-buffer，backlog 由 adjust_replication_buffers.py 在 master 侧处理)
    try:
        new_node.execute_command('CONFIG', 'SET', 'client-output-buffer-limit', 'slave 512MB 64MB 60')
        print_status("Buffer config", "set to 512MB 64MB 60", "OK")
    except Exception as e:
        print_status("Buffer config", str(e), "WARN")
    
    # 注意: repl-backlog-size 应该在 master 侧设置，由 adjust_replication_buffers.py (Step 2.5) 处理
    
    # 3. 将新节点加入集群 (CLUSTER MEET)
    print(f"  Executing CLUSTER MEET {master_host} {master_port}...")
    try:
        new_node.execute_command('CLUSTER', 'MEET', str(master_host), str(master_port))
        print_status("CLUSTER MEET", "executed", "OK")
    except Exception as e:
        print_status("CLUSTER MEET", str(e), "FAIL")
        return False
    
    # 等待gossip传播：验证新节点能看到主节点后再执行REPLICATE
    print("  Waiting for gossip propagation...")
    gossip_ok = False
    for attempt in range(10):
        time.sleep(1)
        try:
            result = new_node.execute_command('CLUSTER', 'NODES')
            if isinstance(result, bytes):
                result = result.decode('utf-8')
            # 检查是否能看到主节点（通过端口判断）
            if f':{master_port}@' in result or f':{master_port}' in result:
                gossip_ok = True
                print_status("Gossip propagation", f"confirmed after {attempt+1}s", "OK")
                break
        except Exception:
            pass
    
    if not gossip_ok:
        print_status("Gossip propagation", "timeout, proceeding anyway", "WARN")
    
    # 4. 设置为从节点 (CLUSTER REPLICATE)
    print(f"  Executing CLUSTER REPLICATE {master_node_id}...")
    try:
        new_node.execute_command('CLUSTER', 'REPLICATE', master_node_id)
        print_status("CLUSTER REPLICATE", "executed", "OK")
    except Exception as e:
        print_status("CLUSTER REPLICATE", str(e), "FAIL")
        return False
    
    return True


def process_shard(shard_config, config, args):
    """处理单个shard (Cluster模式)"""
    shard_idx = shard_config.get('shard_index', 0) + 1
    
    print_header(f"Shard {shard_idx}")
    
    master = shard_config['master']
    master_host = master['host']
    master_port = master['port']
    master_password = config.get('master_password', '')
    
    print_section(f"Master: {master_host}:{master_port}")
    
    # 获取新节点配置 - 每个shard需要3个v7节点
    new_slaves = shard_config.get('new_slaves', [])
    
    # 如果配置不足3个，提示用户
    if len(new_slaves) < 3:
        print_status("WARNING", f"Need 3 v7 replicas per shard, got {len(new_slaves)}", "WARN")
        print("  Add more new_slaves to upgrade_config.json")
    
    if not new_slaves:
        print_status("No new v7 nodes configured", "SKIP", "WARN")
        return []
    
    results = []
    master_node = RedisNode(host=master_host, port=master_port, password=master_password)
    
    for slave_idx, new_slave in enumerate(new_slaves[:3]):  # 最多3个
        new_host = new_slave.get('host')
        new_port = new_slave.get('port', 6379)
        new_password = new_slave.get('password', '')
        new_region = new_slave.get('region', 'A')
        
        if not new_host:
            print_status(f"Skipping replica {slave_idx+1}", "no host configured", "WARN")
            continue
        
        print(f"\n[{slave_idx+1}/3] New v7 Replica ({new_region}): {new_host}:{new_port}")
        
        if args.dry_run:
            print_status("DRY RUN", "would add replica", "INFO")
            results.append({'host': new_host, 'port': new_port, 'status': 'dry_run'})
            continue
        
        # 添加v7从节点
        success = add_v7_replica(
            master_host, master_port, master_password,
            new_host, new_port, new_password,
            None, timeout=args.timeout
        )
        
        if success:
            # 验证版本
            slave_node = RedisNode(new_host, new_port, new_password)
            ver = get_redis_version(slave_node)
            
            # 验证复制状态
            rep_status = verify_replication_status(master_node, slave_node)
            
            print_status("v7 Replica Version", ver)
            print_status("Replication Status", 
                       "connected" if rep_status['connected'] else "disconnected",
                       "OK" if rep_status['connected'] else "FAIL")
            
            results.append({
                'host': new_host,
                'port': new_port,
                'status': 'added',
                'version': ver,
                'replication': rep_status
            })
        else:
            results.append({
                'host': new_host,
                'port': new_port,
                'status': 'failed'
            })
    
    return results


def main():
    args = parse_args()
    
    print_header("Step 3: Add v7 Replicas")
    print(f"  Config: {args.config}")
    print(f"  Dry run: {args.dry_run}")
    
    # 加载配置
    config = load_config(args.config)
    if not config:
        print_status("ERROR", f"Cannot load config from {args.config}", "FAIL")
        sys.exit(1)
    
    shards = config.get('shards', [])
    
    if not shards:
        print_status("ERROR", "No shards found in config", "FAIL")
        sys.exit(1)
    
    # 检测模式
    first_master = shards[0]['master']
    master_node = RedisNode(
        host=first_master['host'],
        port=first_master['port'],
        password=config.get('master_password', '')
    )
    
    # Cluster模式
    print(f"  Using Cluster mode")
    
    # 选择要处理的shard
    if args.shard:
        if args.shard < 1 or args.shard > len(shards):
            print_status("ERROR", f"Invalid shard number: {args.shard}", "FAIL")
            sys.exit(1)
        shards_to_process = [shards[args.shard - 1]]
    else:
        shards_to_process = shards
    
    print(f"  Processing {len(shards_to_process)} shard(s)")
    print(f"  Adding 3 v7 replicas per shard")
    
    all_results = []
    
    for shard in shards_to_process:
        result = process_shard(shard, config, args)
        all_results.append(result)
    
    # 打印摘要
    print_header("Step 3 Summary")
    
    total_added = 0
    total_failed = 0
    
    for idx, results in enumerate(all_results):
        if results:
            shard_idx = idx + 1
            for r in results:
                if r.get('status') == 'added':
                    print_status(f"Shard {shard_idx}", f"Added {r['host']}:{r['port']}", "OK")
                    total_added += 1
                elif r.get('status') == 'failed':
                    print_status(f"Shard {shard_idx}", f"Failed {r['host']}:{r['port']}", "FAIL")
                    total_failed += 1
    
    print(f"\n  Total: {total_added} added, {total_failed} failed")
    print(f"  Expected: {len(shards_to_process) * 3} replicas (3 per shard)")
    
    print_section("Next Steps")
    print("  1. Run verify_replication.py (Step 4) to confirm all replicas are synced")
    print("  2. Run stress_test.py (Step 5) to verify system stability")
    print("  3. Run failover_to_v7.py (Step 6) to promote v7 as master")
    
    if total_failed > 0:
        print("\n⚠ Some replicas failed to add. Check errors above.")
        sys.exit(1)
    
    if args.dry_run:
        print("\n⚠ This was a dry run. Run without --dry-run to execute.")
    
    print("\n" + "=" * 60)
    if total_added > 0:
        print("  ✓ PASS - v7 replicas added successfully")
    else:
        print("  ✗ FAIL - No replicas added")
    print("=" * 60)


if __name__ == '__main__':
    main()
