#!/usr/bin/env python3
"""
Step 2: 升级前检查脚本
验证集群健康状态、复制状态、配置兼容性

检查项:
- 集群健康状态
- 所有节点版本
- 复制状态
- 内存和配置
- 命令兼容性
"""

import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    RedisNode, print_header, print_section, print_status, print_expect,
    get_redis_version, get_rdb_version, get_cluster_info, check_node_health,
    verify_command_compatibility, verify_data_encoding, check_replication_buffers,
    verify_v6_v7_config_diff, load_config, confirm_action
)


DEFAULT_CONFIG = 'cluster_config.json'


def parse_args():
    parser = argparse.ArgumentParser(
        description="Step 2: Pre-Upgrade Check - 验证集群是否准备好升级"
    )
    parser.add_argument(
        '--config', '-c',
        default=DEFAULT_CONFIG,
        help=f'集群配置文件路径 (default: {DEFAULT_CONFIG})'
    )
    parser.add_argument(
        '--skip-warnings',
        action='store_true',
        help='跳过警告确认'
    )
    return parser.parse_args()


def check_all_nodes(config: dict) -> dict:
    """检查所有节点状态"""
    results = {
        'total': 0,
        'alive': 0,
        'v6_only': 0,
        'errors': []
    }
    
    nodes = config.get('nodes', [])
    results['total'] = len(nodes)
    
    for node_info in nodes:
        host = node_info['host']
        port = node_info.get('port', 6379)
        password = node_info.get('password')
        
        print_section(f"Checking {host}:{port}")
        
        node = RedisNode(host=host, port=port, password=password)
        
        # 健康检查
        health = check_node_health(node)
        
        if health['alive']:
            results['alive'] += 1
            print_status("Status", "ALIVE", "OK")
            print_status("Redis Version", health['version'])
            
            # 检查版本
            if '6.2' in health['version']:
                results['v6_only'] += 1
                print_status("Version Check", "v6.2.x", "OK")
            else:
                results['errors'].append(f"{host}:{port} is not v6.2.x: {health['version']}")
                print_status("Version Check", f"NOT v6.2: {health['version']}", "WARN")
            
            # 检查cluster状态
            print_status("Cluster State", health['cluster_state'], "OK")
            
            # 检查RDB版本
            rdb_ver = get_rdb_version(node)
            print_status("RDB Version", rdb_ver)
            print_expect("RDB version should be 9", "9", str(rdb_ver))
            
        else:
            results['errors'].append(f"{host}:{port} is not alive")
            print_status("Status", "NOT ALIVE", "FAIL")
            for err in health['errors']:
                print_status("Error", err, "FAIL")
    
    return results


def check_cluster_state(config: dict) -> dict:
    """检查集群状态"""
    results = {
        'healthy': False,
        'details': {}
    }
    
    # 使用第一个节点检查集群
    nodes = config.get('nodes', [])
    if not nodes:
        return results
    
    first = nodes[0]
    node = RedisNode(
        host=first['host'],
        port=first.get('port', 6379),
        password=first.get('password')
    )
    
    cluster_info = get_cluster_info(node)
    
    results['details'] = cluster_info
    results['healthy'] = cluster_info.get('cluster_state') == 'ok'
    
    print_section("Cluster State Check")
    print_status("Cluster State", cluster_info.get('cluster_state', 'unknown'))
    print_status("Slots Assigned", cluster_info.get('cluster_slots_assigned', 'unknown'))
    print_status("Slots OK", cluster_info.get('cluster_slots_ok', 'unknown'))
    print_status("Slots Fail", cluster_info.get('cluster_slots_fail', 'unknown'))
    print_status("Cluster Nodes", cluster_info.get('cluster_nodes', 'unknown'))
    
    print_expect("Cluster state should be 'ok'", "ok", cluster_info.get('cluster_state'))
    
    return results


def check_replication_status(config: dict) -> dict:
    """检查复制状态"""
    results = {
        'all_healthy': True,
        'shards': []
    }
    
    # 遍历所有节点，查找主从关系
    nodes = config.get('nodes', [])
    
    # 按shard分组
    shards = {}
    for node_info in nodes:
        host = node_info['host']
        port = node_info.get('port', 6379)
        password = node_info.get('password')
        
        node = RedisNode(host=host, port=port, password=password)
        info = node.info('replication')
        role = info.get('role', 'unknown')
        
        if role == 'master':
            # 找到主节点
            shard_key = f"{host}:{port}"
            shards[shard_key] = {
                'master': {'host': host, 'port': port, 'connected_slaves': 0},
                'slaves': []
            }
        elif role == 'slave':
            # 找到从节点，关联主节点
            master_host = info.get('master_host', '')
            master_port = info.get('master_port', 0)
            master_link_status = info.get('master_link_status', 'down')
            
            for shard_key in shards:
                shard = shards[shard_key]
                if (shard['master']['host'] == master_host and 
                    shard['master']['port'] == master_port):
                    shard['slaves'].append({
                        'host': host,
                        'port': port,
                        'master_link_status': master_link_status,
                        'slave_repl_offset': info.get('slave_repl_offset', 0)
                    })
                    break
    
    print_section("Replication Status Check")
    
    for shard_key, shard in shards.items():
        print_section(f"Shard: {shard_key}")
        
        master_info = RedisNode(
            host=shard['master']['host'],
            port=shard['master']['port']
        ).info('replication')
        
        connected_slaves = master_info.get('connected_slaves', 0)
        print_status("Master", shard_key, "OK")
        print_status("Connected Slaves", connected_slaves)
        
        # 检查每个从节点
        for slave in shard['slaves']:
            slave_node = RedisNode(host=slave['host'], port=slave['port'])
            slave_info = slave_node.info('replication')
            
            status = slave_info.get('master_link_status', 'down')
            offset = slave_info.get('slave_repl_offset', 0)
            
            print_status(
                f"Slave {slave['host']}:{slave['port']}",
                f"link:{status}, offset:{offset}",
                "OK" if status == 'up' else "FAIL"
            )
            
            if status != 'up':
                results['all_healthy'] = False
                results['shards'].append({
                    'master': shard_key,
                    'slave': f"{slave['host']}:{slave['port']}",
                    'issue': f"master_link_status={status}"
                })
        
        # 记录
        results['shards'].append({
            'master': shard_key,
            'slaves_count': len(shard['slaves']),
            'all_connected': all(s.get('master_link_status') == 'up' for s in shard['slaves'])
        })
    
    return results


def check_memory_and_config(config: dict) -> dict:
    """检查内存和配置"""
    results = {
        'nodes': []
    }
    
    print_section("Memory & Config Check")
    
    for node_info in config.get('nodes', []):
        host = node_info['host']
        port = node_info.get('port', 6379)
        password = node_info.get('password')
        
        node = RedisNode(host=host, port=port, password=password)
        
        info = node.info()
        
        used_memory = info.get('used_memory_human', 'unknown')
        maxmemory = info.get('maxmemory_human', 'unknown')
        maxmemory_policy = info.get('maxmemory_policy', 'unknown')
        
        print_section(f"Node: {host}:{port}")
        print_status("Used Memory", used_memory)
        print_status("Max Memory", maxmemory)
        print_status("Eviction Policy", maxmemory_policy)
        
        # 计算使用率
        if maxmemory != '0B' and maxmemory != 'unknown':
            try:
                # 简单解析
                used = float(used_memory.replace('GB', '').replace('MB', ''))
                max_ = float(maxmemory.replace('GB', '').replace('MB', ''))
                if 'GB' in maxmemory:
                    max_ = max_ * 1024
                if 'GB' in used_memory:
                    used = used * 1024
                
                usage_percent = (used / max_) * 100
                print_status("Usage", f"{usage_percent:.1f}%")
                
                if usage_percent > 70:
                    print_status("WARNING", "Memory usage > 70%", "WARN")
                else:
                    print_status("Memory Check", "OK", "OK")
            except:
                pass
        
        # 检查复制缓冲区配置
        buffers = check_replication_buffers(node)
        print_status("Replica Buffer", buffers['current'].get('client_output_buffer_limit_replica', 'N/A'))
        print_expect("Recommended", "512MB 64MB 60", 
                     buffers['current'].get('client_output_buffer_limit_replica', 'N/A'))
        
        results['nodes'].append({
            'host': host,
            'port': port,
            'used_memory': used_memory,
            'maxmemory': maxmemory,
            'maxmemory_policy': maxmemory_policy
        })
    
    return results


def check_command_compatibility(config: dict) -> dict:
    """检查命令兼容性"""
    results = {
        'compatible': True,
        'details': {}
    }
    
    print_section("Command Compatibility Check")
    
    # 选一个主节点测试
    nodes = config.get('nodes', [])
    if not nodes:
        return results
    
    master_node = None
    for node_info in nodes:
        node = RedisNode(
            host=node_info['host'],
            port=node_info.get('port', 6379),
            password=node_info.get('password')
        )
        if node.info('replication').get('role') == 'master':
            master_node = node
            break
    
    if not master_node:
        print_status("ERROR", "No master node found", "FAIL")
        return results
    
    print(f"Testing on master: {master_node.host}:{master_node.port}")
    
    # 测试命令兼容性
    cmd_results = verify_command_compatibility(master_node)
    results['details']['commands'] = cmd_results
    
    for cmd, result in cmd_results.items():
        if cmd == 'error':
            print_status(f"Command {cmd}", str(result), "FAIL")
            results['compatible'] = False
        elif isinstance(result, dict):
            supported = result.get('supported', False)
            print_status(f"Command {cmd}", "Supported" if supported else "Not Supported",
                         "OK" if supported else "WARN")
    
    # 测试数据结构编码
    print_section("Data Encoding Check")
    encoding_results = verify_data_encoding(master_node)
    results['details']['encoding'] = encoding_results
    
    for dtype, encoding in encoding_results.items():
        if dtype != 'error':
            print_status(f"{dtype}", encoding, "OK")
    
    # 测试 v6/v7 配置差异
    print_section("v6/v7 Configuration Differences Check")
    print("  Checking key configuration differences (see design.md 2.1)")
    config_results = verify_v6_v7_config_diff(master_node)
    results['details']['config_diff'] = config_results
    
    for param, result in config_results.items():
        if param == 'error':
            continue
        current = result.get('current', 'N/A')
        impact = result.get('impact', '')
        is_v7_default = result.get('is_v7_default', False)
        warning = result.get('warning', False)
        
        status = "WARN" if (is_v7_default or warning) else "OK"
        detail = f"{current} (v6:{result.get('v6_default')}, v7:{result.get('v7_default')})"
        print_status(f"{param}", detail, status)
        if impact:
            print(f"    Impact: {impact}")
    
    return results


def check_rdb_version(config: dict) -> dict:
    """检查RDB版本兼容性"""
    results = {
        'compatible': True,
        'details': {}
    }
    
    print_section("RDB Version Check")
    print("  Note: v6 RDB=9, v7 RDB=11")
    print("  During upgrade, v6 nodes CANNOT restart (will fail to load v7 RDB)")
    
    for node_info in config.get('nodes', []):
        host = node_info['host']
        port = node_info.get('port', 6379)
        password = node_info.get('password')
        
        node = RedisNode(host=host, port=port, password=password)
        version = get_redis_version(node)
        rdb_ver = get_rdb_version(node)
        
        results['details'][f"{host}:{port}"] = {
            'version': version,
            'rdb_version': rdb_ver
        }
        
        print_status(f"Node {host}:{port}", f"Redis={version}, RDB={rdb_ver}")
        
        if '6.2' in version and rdb_ver != 9:
            print_status("WARNING", f"Expected RDB=9 for v6, got {rdb_ver}", "WARN")
    
    return results


def main():
    args = parse_args()
    
    print_header("Step 2: Pre-Upgrade Check")
    print(f"  Config: {args.config}")
    
    # 加载配置
    config = load_config(args.config)
    if not config:
        print_status("ERROR", f"Cannot load config from {args.config}", "FAIL")
        sys.exit(1)
    
    all_passed = True
    warnings = []
    
    # 1. 检查所有节点
    print_section("1. Node Health Check")
    node_results = check_all_nodes(config)
    if node_results['alive'] != node_results['total']:
        all_passed = False
        warnings.append(f"Some nodes are not alive: {node_results['alive']}/{node_results['total']}")
    
    if node_results['v6_only'] != node_results['total']:
        warnings.append("Not all nodes are v6.2.x")
    
    # 2. 检查集群状态
    print_section("2. Cluster State Check")
    cluster_results = check_cluster_state(config)
    if not cluster_results['healthy']:
        all_passed = False
        warnings.append("Cluster state is not OK")
    
    # 3. 检查复制状态
    print_section("3. Replication Status Check")
    rep_results = check_replication_status(config)
    if not rep_results['all_healthy']:
        all_passed = False
        warnings.append("Some replication links are not healthy")
    
    # 4. 检查内存和配置
    print_section("4. Memory & Config Check")
    mem_results = check_memory_and_config(config)
    
    # 5. 检查RDB版本
    print_section("5. RDB Version Check")
    rdb_results = check_rdb_version(config)
    
    # 6. 检查命令兼容性
    print_section("6. Command Compatibility Check")
    cmd_results = check_command_compatibility(config)
    
    # 打印摘要
    print_header("Pre-Upgrade Check Summary")
    
    if all_passed:
        print_status("Overall Status", "PASSED", "OK")
    else:
        print_status("Overall Status", "FAILED - See warnings above", "FAIL")
    
    if warnings:
        print_section("Warnings")
        for w in warnings:
            print_status("WARNING", w, "WARN")
    
    print_section("Key Points")
    print("  1. All nodes should be v6.2.x")
    print("  2. Cluster state should be 'ok'")
    print("  3. All replication links should be 'up'")
    print("  4. Memory usage should be < 70%")
    print("  5. v6 nodes CANNOT restart during upgrade (RDB incompatible)")
    print("  6. Consider increasing replication buffer for v7 nodes")
    
    # 确认继续
    print("\n" + "=" * 60)
    if all_passed:
        if args.skip_warnings or confirm_action("\nProceed with upgrade?"):
            print("\n✓ Ready for upgrade!")
            print("  ✓ PASS - Pre-upgrade check passed")
        else:
            print("\nAborted.")
            print("  ⚠ SKIPPED - User aborted")
            sys.exit(1)
    else:
        print("\n✗ Please fix the issues above before proceeding!")
        print("  ✗ FAIL - Pre-upgrade check failed")
        sys.exit(1)
    print("=" * 60)


if __name__ == '__main__':
    main()
