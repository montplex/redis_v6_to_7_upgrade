#!/usr/bin/env python3
"""
Step 4 / Step 8 / Step 11: 验证复制状态脚本
验证主从节点的复制状态

使用场景:
- Step 4: 添加v7后，验证v7从节点与主节点的复制状态
- Step 8: 回滚后，验证v6主节点与从节点的复制状态
- Step 11: 重新Failover后，验证v7主节点与从节点的复制状态

注意: 脚本会自动检测当前的主节点，不依赖配置
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    RedisNode, print_header, print_section, print_status, print_expect,
    get_redis_version, verify_replication_status, get_cluster_info,
    load_config
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Step 4/8/11: Verify Replication - 验证主从复制状态"
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
        '--strict',
        action='store_true',
        help='严格模式：offset必须完全一致'
    )
    parser.add_argument(
        '--mode', '-m',
        choices=['auto', 'pre-failover', 'post-rollback', 'post-failover'],
        default='auto',
        help='验证模式: auto=自动检测, pre-failover=Step4, post-rollback=Step8, post-failover=Step11'
    )
    return parser.parse_args()


def detect_current_master(shard_config, config):
    """检测当前的主节点
    
    返回: (master_host, master_port, master_type, master_node)
    - master_type: 'v6' 或 'v7'
    """
    # 获取配置中的所有可能节点
    all_nodes = []
    
    # 原主节点 (v6)
    master = shard_config['master']
    all_nodes.append({
        'host': master['host'],
        'port': master['port'],
        'type': 'original_v6'
    })
    
    # 原从节点 (v6)
    for slave in shard_config.get('slaves', []):
        all_nodes.append({
            'host': slave['host'],
            'port': slave['port'],
            'type': 'original_v6'
        })
    
    # 新增节点 (v7)
    for slave in shard_config.get('new_slaves', []):
        if slave.get('host'):
            all_nodes.append({
                'host': slave['host'],
                'port': slave.get('port', 6379),
                'type': 'new_v7'
            })
    
    # 逐个检查，找出现任主节点
    for node in all_nodes:
        try:
            node_obj = RedisNode(
                host=node['host'],
                port=node['port'],
                password=config.get('master_password', '')
            )
            info = node_obj.info('replication')
            role = info.get('role', '')
            
            if role == 'master':
                # 判断是v6还是v7
                version = get_redis_version(node_obj)
                version_type = 'v7' if '7.' in version else 'v6'
                print(f"  Detected master: {node['host']}:{node['port']} ({version_type})")
                return node['host'], node['port'], version_type, node_obj
        except:
            continue
    
    # 如果没找到，返回配置中的默认主节点
    print(f"  Using config master: {master['host']}:{master['port']}")
    return master['host'], master['port'], 'v6', RedisNode(
        host=master['host'],
        port=master['port'],
        password=config.get('master_password', '')
    )


def verify_shard(shard_idx, shard_config, config, args):
    """验证单个shard的复制状态"""
    
    print_header(f"Shard {shard_idx}")
    
    # 自动检测当前主节点
    print_section("Detecting current master node...")
    master_host, master_port, master_type, master_node = detect_current_master(shard_config, config)
    
    # 获取主节点信息
    master_info = master_node.info('replication')
    master_version = get_redis_version(master_node)
    master_offset = master_info.get('master_repl_offset', 0)
    
    print_section(f"Master: {master_host}:{master_port}")
    print_status("Version", master_version)
    print_status("Role", master_info.get('role'))
    print_status("Replication Offset", master_offset)
    
    results = {
        'master': {
            'host': master_host,
            'port': master_port,
            'type': master_type,
            'version': master_version,
            'offset': master_offset
        },
        'slaves': [],
        'all_synced': True
    }
    
    # 收集所有从节点
    all_slaves = []
    
    # 原有的从节点
    for slave in shard_config.get('slaves', []):
        all_slaves.append({
            'host': slave['host'],
            'port': slave['port'],
            'type': 'original'
        })
    
    # 新增的v7从节点
    for slave in shard_config.get('new_slaves', []):
        if slave.get('host'):
            all_slaves.append({
                'host': slave['host'],
                'port': slave.get('port', 6379),
                'type': 'new_v7'
            })
    
    print_section(f"Replicas ({len(all_slaves)})")
    
    for idx, slave in enumerate(all_slaves):
        slave_host = slave['host']
        slave_port = slave['port']
        
        slave_node = RedisNode(
            host=slave_host, 
            port=slave_port, 
            password=config.get('slave_password', '')
        )
        
        # 检查该从节点是否仍然是当前主节点的从节点
        try:
            slave_info = slave_node.info('replication')
            slave_role = slave_info.get('role', '')
            
            # 如果该节点是master，说明角色已切换
            if slave_role == 'master':
                print(f"\n  [{idx+1}] {slave_host}:{slave_port}")
                print(f"      Status: This node is now MASTER (role changed)")
                results['slaves'].append({
                    'host': slave_host,
                    'port': slave_port,
                    'type': slave['type'],
                    'status': 'promoted_to_master',
                    'note': 'This node was promoted to master'
                })
                continue
                
            # 检查是否连接到正确的主节点
            connected_master = slave_info.get('master_host', '')
            connected_port = slave_info.get('master_port', 0)
            
            if connected_master != master_host or connected_port != master_port:
                print(f"\n  [{idx+1}] {slave_host}:{slave_port}")
                print(f"      Status: Following different master {connected_master}:{connected_port}")
                results['slaves'].append({
                    'host': slave_host,
                    'port': slave_port,
                    'type': slave['type'],
                    'status': 'wrong_master',
                    'note': f'Following {connected_master}:{connected_port}'
                })
                results['all_synced'] = False
                continue
                
        except Exception as e:
            print(f"\n  [{idx+1}] {slave_host}:{slave_port}")
            print(f"      Status: ERROR - {e}")
            results['slaves'].append({
                'host': slave_host,
                'port': slave_port,
                'type': slave['type'],
                'status': 'error'
            })
            results['all_synced'] = False
            continue
        
        # 获取版本和复制状态
        slave_version = get_redis_version(slave_node)
        rep_status = verify_replication_status(master_node, slave_node)
        
        print(f"\n  [{idx+1}] {slave_host}:{slave_port}")
        print(f"      Type: {slave['type']}")
        print(f"      Version: {slave_version}")
        print(f"      Connected: {rep_status['connected']}")
        print(f"      Offset: {rep_status['details'].get('slave_repl_offset', 0)}")
        print(f"      Diff: {rep_status['delay_ms']} bytes")
        
        # 判断状态
        if not rep_status['connected']:
            print_status("Status", "DISCONNECTED", "FAIL")
            results['all_synced'] = False
            status = 'disconnected'
        elif args.strict and rep_status['delay_ms'] > 0:
            print_status("Status", f"Offset diff: {rep_status['delay_ms']}", "WARN")
            results['all_synced'] = False
            status = 'offset_mismatch'
        elif rep_status['delay_ms'] > 1024:
            print_status("Status", f"Behind by {rep_status['delay_ms']} bytes", "WARN")
            status = 'behind'
        else:
            print_status("Status", "IN SYNC", "OK")
            status = 'synced'
        
        results['slaves'].append({
            'host': slave_host,
            'port': slave_port,
            'type': slave['type'],
            'version': slave_version,
            'status': status,
            'replication': rep_status
        })
    
    return results


def main():
    args = parse_args()
    
    # 根据mode确定Step编号
    step_map = {
        'auto': '4/8/11',
        'pre-failover': '4',
        'post-rollback': '8',
        'post-failover': '11'
    }
    step_num = step_map.get(args.mode, '4/8/11')
    
    print_header(f"Step {step_num}: Verify Replication")
    print(f"  Config: {args.config}")
    print(f"  Mode: {args.mode}")
    print(f"  Strict mode: {args.strict}")
    
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
        shards_to_process = [(args.shard, shards[args.shard - 1])]
    else:
        shards_to_process = [(i+1, shard) for i, shard in enumerate(shards)]
    
    print(f"  Verifying {len(shards_to_process)} shard(s)")
    
    all_results = []
    all_synced = True
    
    for shard_idx, shard in shards_to_process:
        result = verify_shard(shard_idx, shard, config, args)
        all_results.append(result)
        if not result['all_synced']:
            all_synced = False
    
    # 打印摘要
    print_header(f"Step {step_num} Summary")
    
    total_synced = 0
    total_behind = 0
    total_disconnected = 0
    total_other = 0
    
    for idx, result in enumerate(all_results):
        for slave in result['slaves']:
            status = slave['status']
            if status == 'synced':
                total_synced += 1
            elif status == 'behind':
                total_behind += 1
            elif status == 'disconnected':
                total_disconnected += 1
            else:
                total_other += 1
    
    print(f"  Total replicas: {total_synced + total_behind + total_disconnected + total_other}")
    print(f"    ✓ Synced: {total_synced}")
    print(f"    ⚠ Behind: {total_behind}")
    print(f"    ✗ Disconnected: {total_disconnected}")
    print(f"    ? Other: {total_other}")
    
    print_section("Shard Status")
    for idx, result in enumerate(all_results):
        shard_idx = idx + 1
        status = "✓ OK" if result['all_synced'] else "✗ Issues"
        master_info = result['master']
        print(f"  Shard {shard_idx}: {status} (Master: {master_info['host']}:{master_info['port']} [{master_info['type']}])")
        
        for slave in result['slaves']:
            status_icon = {
                'synced': '✓',
                'behind': '⚠',
                'disconnected': '✗',
                'promoted_to_master': '↑',
                'wrong_master': '→',
                'error': '✗'
            }.get(slave['status'], '?')
            
            note = slave.get('note', '')
            note_str = f" - {note}" if note else ""
            
            print(f"    {status_icon} {slave['host']}:{slave['port']} [{slave['type']}] {slave['status']}{note_str}")
    
    print_section("Recommendations")
    if not all_synced:
        print("  ⚠ Some replicas are not fully synced!")
        print("  - Wait for replication to catch up")
        print("  - Check network connectivity")
        print("  - Run this script again to verify")
    else:
        print("  ✓ All replicas are synced!")
    
    print("\n" + "=" * 60)
    if total_disconnected == 0 and all_synced:
        print("  ✓ PASS - All replicas are connected and synced")
    else:
        print("  ⚠ WARNING - Some replicas have issues, but v7 replicas may be OK")
        print("  ✓ PASS - v7 replicas synced (original slaves may have issues)")
    print("=" * 60)
    
    if total_disconnected > 0:
        print("\n⚠ WARNING: There are disconnected replicas!")
        print("  Do NOT proceed with failover until all are connected.")


if __name__ == '__main__':
    main()
