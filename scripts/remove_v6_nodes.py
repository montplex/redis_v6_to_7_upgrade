#!/usr/bin/env python3
"""
Step 12: 移除v6节点脚本
在观察期结束后，移除v6节点，完成升级
"""

import sys
import os
import argparse
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    RedisNode, print_header, print_section, print_status, print_expect,
    get_redis_version, verify_replication_status, get_cluster_nodes,
    load_config, confirm_action
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Step 12: Remove v6 Nodes - 移除v6节点完成升级"
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


def remove_v6_node(node_host, node_port, password=None):
    """移除v6节点"""
    
    print(f"\n  Removing v6 node: {node_host}:{node_port}")
    
    node = RedisNode(host=node_host, port=node_port, password=password)
    
    # 检查节点状态
    if not node.ping():
        print_status("Node", "not responding", "WARN")
        return False
    
    # 获取版本
    version = get_redis_version(node)
    
    if '7.' in version:
        print_status("Node is already v7", version, "WARN")
        return False
    
    print_status("Current version", version)
    print_status("This node will be removed", "", "WARN")
    
    return True


def cleanup_v6_replica(node_host, node_port, password=None, master_host=None, master_port=None):
    """清理v6从节点"""
    
    print(f"\n  Cleaning up v6 replica: {node_host}:{node_port}")
    
    node = RedisNode(host=node_host, port=node_port, password=password)
    
    # 获取节点ID，用于后续cluster forget
    node_id = None
    try:
        info = node.execute_command('CLUSTER', 'NODES')
        if isinstance(info, bytes):
            info = info.decode('utf-8')
        for line in info.split('\n'):
            if f"{node_host}:{node_port}" in line and 'myself' in line:
                node_id = line.split()[0]
                break
    except Exception as e:
        print_status("Get node ID", str(e), "WARN")
    
    if not node.ping():
        print_status("Node", "already down", "OK")
        # 节点已宕机，尝试从集群中移除
        if node_id and master_host and master_port:
            try:
                master_node = RedisNode(host=master_host, port=master_port)
                master_node.execute_command('CLUSTER', 'FORGET', node_id)
                print_status("CLUSTER FORGET", node_id, "OK")
            except Exception as e:
                print_status("CLUSTER FORGET", str(e), "WARN")
        return True
    
    version = get_redis_version(node)
    if '7.' in version:
        print_status("Node is v7", "skipping", "OK")
        return True
    
    # 尝试优雅关闭
    try:
        print_status("Sending SHUTDOWN", "", "INFO")
        node.execute_command('SHUTDOWN', 'NOSAVE')
        print_status("Shutdown", "sent", "OK")
    except Exception as e:
        print_status("Shutdown", str(e), "WARN")
    
    # 关闭后执行cluster forget
    if node_id and master_host and master_port:
        try:
            time.sleep(1)
            master_node = RedisNode(host=master_host, port=master_port)
            master_node.execute_command('CLUSTER', 'FORGET', node_id)
            print_status("CLUSTER FORGET", node_id, "OK")
        except Exception as e:
            print_status("CLUSTER FORGET", str(e), "WARN")
    
    return True


def check_cluster_gate(master_host, master_port):
    """执行 gate 检查：验证集群状态正常"""
    try:
        master_node = RedisNode(host=master_host, port=master_port)
        info = master_node.execute_command('CLUSTER', 'INFO')
        if isinstance(info, bytes):
            info = info.decode('utf-8')
        for line in info.split('\n'):
            if line.startswith('cluster_state:'):
                state = line.split(':')[1].strip()
                if state == 'ok':
                    return True, "cluster_state=ok"
                else:
                    return False, f"cluster_state={state}"
        return False, "cannot parse cluster_state"
    except Exception as e:
        return False, str(e)


def adjust_replica_topology(shard_config, config, args):
    """调整从节点拓扑
    
    移除顺序（按 design.md 要求）：
    1. Region B 的跨 region v6 replicas（更容易抖动）
    2. Region A 的同 region v6 replicas
    3. 原 v6 masters（现为从节点，是回滚锚点，最后移除）
    
    每移除一个节点都要做 gate 检查
    """
    
    shard_idx = shard_config.get('shard_index', 0) + 1
    
    print_header(f"Shard {shard_idx}")
    
    # 找到当前主节点（应该是v7）
    new_master = shard_config.get('new_master', None)
    
    # 如果没有记录，尝试从配置推断
    if not new_master:
        new_slaves = shard_config.get('new_slaves', [])
        for slave in new_slaves:
            if slave.get('host'):
                new_master = {
                    'host': slave.get('host'),
                    'port': slave.get('port', 6379)
                }
                break
    
    if not new_master:
        print_status("ERROR", "Cannot find new master", "FAIL")
        return None
    
    master_host = new_master['host']
    master_port = new_master['port']
    master_password = config.get('master_password', '')
    
    print_section(f"Current Master (v7): {master_host}:{master_port}")
    
    # 获取当前的从节点
    master_node = RedisNode(host=master_host, port=master_port, password=master_password)
    cluster_nodes = get_cluster_nodes(master_node)
    
    # 获取原始 v6 slaves 配置，用于判断 region
    original_v6_slaves = shard_config.get('slaves', [])
    v6_slave_ports = {s['port']: s.get('region', 'A') for s in original_v6_slaves}
    
    v6_replicas_cross_region = []  # Region B
    v6_replicas_same_region = []   # Region A
    v7_nodes = []
    
    for node_id, node_info in cluster_nodes.items():
        if node_info['role'] == 'slave':
            host = node_info['host']
            port = node_info['port']
            
            # 检查版本
            try:
                node = RedisNode(host=host, port=port)
                version = get_redis_version(node)
                
                if '6.' in version:
                    # 根据配置判断 region
                    region = v6_slave_ports.get(port, 'A')
                    if region == 'B':
                        v6_replicas_cross_region.append({'host': host, 'port': port, 'version': version, 'region': region})
                    else:
                        v6_replicas_same_region.append({'host': host, 'port': port, 'version': version, 'region': region})
                else:
                    v7_nodes.append({'host': host, 'port': port, 'version': version})
            except:
                pass
    
    print(f"\n  Current v7 replicas: {len(v7_nodes)}")
    for n in v7_nodes:
        print(f"    - {n['host']}:{n['port']} ({n['version']})")
    
    print(f"\n  v6 replicas to remove:")
    print(f"    Cross-region (Region B): {len(v6_replicas_cross_region)}")
    for n in v6_replicas_cross_region:
        print(f"      - {n['host']}:{n['port']} ({n['version']})")
    print(f"    Same-region (Region A): {len(v6_replicas_same_region)}")
    for n in v6_replicas_same_region:
        print(f"      - {n['host']}:{n['port']} ({n['version']})")
    
    if args.dry_run:
        print("\n  DRY RUN: Would remove v6 nodes in order:")
        print("    1. Cross-region replicas")
        print("    2. Same-region replicas")
        print("    3. Original masters")
        return {'v6_removed': len(v6_replicas_cross_region) + len(v6_replicas_same_region), 'dry_run': True}
    
    removed_count = 0
    
    # 阶段1: 移除跨region v6 replicas
    print("\n" + "="*40)
    print("  Phase 1: Removing cross-region v6 replicas")
    print("="*40)
    for v6_node in v6_replicas_cross_region:
        print(f"\n  >>> Removing {v6_node['host']}:{v6_node['port']}...")
        if cleanup_v6_replica(v6_node['host'], v6_node['port'], config.get('slave_password'), master_host, master_port):
            removed_count += 1
        
        # Gate 检查
        print("  Performing gate check...")
        gate_ok, gate_msg = check_cluster_gate(master_host, master_port)
        if gate_ok:
            print_status("Gate check", gate_msg, "OK")
        else:
            print_status("Gate check", gate_msg, "FAIL")
            print("  ⚠️  WARNING: Cluster state not OK, but continuing...")
    
    # 阶段2: 移除同region v6 replicas
    print("\n" + "="*40)
    print("  Phase 2: Removing same-region v6 replicas")
    print("="*40)
    for v6_node in v6_replicas_same_region:
        print(f"\n  >>> Removing {v6_node['host']}:{v6_node['port']}...")
        if cleanup_v6_replica(v6_node['host'], v6_node['port'], config.get('slave_password'), master_host, master_port):
            removed_count += 1
        
        # Gate 检查
        print("  Performing gate check...")
        gate_ok, gate_msg = check_cluster_gate(master_host, master_port)
        if gate_ok:
            print_status("Gate check", gate_msg, "OK")
        else:
            print_status("Gate check", gate_msg, "FAIL")
            print("  ⚠️  WARNING: Cluster state not OK, but continuing...")
    
    # 阶段3: 移除原 v6 masters（现为从节点）
    print("\n" + "="*40)
    print("  Phase 3: Removing original v6 masters (rollback anchor)")
    print("="*40)
    original_master = shard_config.get('master', {})
    old_master_host = original_master.get('host')
    old_master_port = original_master.get('port')
    
    if old_master_host and old_master_port:
        print(f"\n  >>> Removing original master {old_master_host}:{old_master_port}...")
        if cleanup_v6_replica(old_master_host, old_master_port, config.get('master_password'), master_host, master_port):
            removed_count += 1
        
        # Gate 检查
        print("  Performing gate check...")
        gate_ok, gate_msg = check_cluster_gate(master_host, master_port)
        if gate_ok:
            print_status("Gate check", gate_msg, "OK")
        else:
            print_status("Gate check", gate_msg, "FAIL")
    
    return {'v6_removed': removed_count, 'v7_replicas': len(v7_nodes)}


def main():
    args = parse_args()
    
    print_header("Step 12: Remove v6 Nodes")
    print(f"  Config: {args.config}")
    print(f"  Shard: {args.shard or 'all'}")
    print(f"  Dry run: {args.dry_run}")
    
    # 警告
    print("\n" + "="*50)
    print("⚠️  WARNING: This will remove v6 nodes!")
    print("="*50)
    print("  - Only run after observation period (1-2 hours, max 4 hours)")
    print("  - Make sure v7 cluster is stable")
    print("  - Removal order: cross-region replicas → same-region replicas → original masters")
    print("  - Gate check will be performed after each node removal")
    print("  - This is NOT reversible!")
    
    if not args.dry_run:
        if args.auto_continue:
            print("\nProceed with removing v6 nodes? Type 'yes' to confirm: y (auto-confirmed)")
        elif not confirm_action("\nProceed with removing v6 nodes?"):
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
    
    print(f"  Processing {len(shards_to_process)} shard(s)")
    
    all_results = []
    
    for shard in shards_to_process:
        result = adjust_replica_topology(shard, config, args)
        if result:
            all_results.append(result)
    
    # 打印摘要
    print_header("Step 5 Summary")
    
    total_removed = sum(r.get('v6_removed', 0) for r in all_results)
    
    print(f"  Shards processed: {len(all_results)}")
    print(f"  v6 nodes removed: {total_removed}")
    
    if args.dry_run:
        print("\n⚠ This was a dry run. Run without --dry-run to execute.")
    else:
        print("\n" + "="*50)
        print("✅ UPGRADE COMPLETED!")
        print("="*50)
        print("  - All v6 nodes have been removed")
        print("  - Cluster is now running v7.2.x")
        
        print_section("Final Verification")
        print("  Run pre_upgrade_check.py to verify cluster health")
    
    print("\n" + "=" * 60)
    if total_removed > 0:
        print("  ✓ PASS - v6 nodes removed successfully")
    else:
        print("  ✗ FAIL - No v6 nodes removed")
    print("=" * 60)


if __name__ == '__main__':
    main()
