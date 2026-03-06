#!/usr/bin/env python3
"""
Step 0: 准备集群样本
用于收集和记录当前Redis Cluster的拓扑结构、节点状态、配置信息
生成升级所需的配置文件

支持两种模式：
1. 连接真实集群：扫描现有Redis Cluster
2. 本地模拟：在同一台机器上用不同端口模拟集群
"""

import sys
import os
import json
import argparse
import subprocess
import time
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    RedisNode, print_header, print_section, print_status, print_expect,
    get_redis_version, get_rdb_version, get_cluster_nodes, get_cluster_info,
    load_config, save_config, confirm_action
)


DEFAULT_CONFIG = 'cluster_config.json'


def parse_args():
    parser = argparse.ArgumentParser(
        description="Step 0: Prepare Redis Cluster Sample"
    )
    parser.add_argument(
        '--mode', '-m',
        choices=['collect', 'simulate'],
        default='collect',
        help='模式: collect=连接真实集群, simulate=本地模拟 (default: collect)'
    )
    parser.add_argument(
        '--config', '-c',
        default=DEFAULT_CONFIG,
        help='配置文件路径'
    )
    parser.add_argument(
        '--output', '-o',
        default='upgrade_config.json',
        help='输出文件路径 (default: upgrade_config.json)'
    )
    parser.add_argument(
        '--base-port', '-p',
        type=int,
        default=6379,
        help='基础端口 (模拟模式用, default: 6379)'
    )
    parser.add_argument(
        '--shards', '-s',
        type=int,
        default=3,
        help='Shard数量 (模拟模式用, default: 3)'
    )
    parser.add_argument(
        '--replicas', '-r',
        type=int,
        default=2,
        help='每个主节点的从节点数量 (模拟模式用, default: 2)'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='强制覆盖已存在的配置文件'
    )
    parser.add_argument(
        '--redis-bin',
        default='redis-server',
        help='Redis二进制文件路径 (模拟模式用)'
    )
    return parser.parse_args()


def find_redis_bin():
    """查找Redis二进制文件"""
    paths = [
        'redis-server',
        '/usr/bin/redis-server',
        '/usr/local/bin/redis-server',
        '/home/kerry/ws/redis/src/redis-server',
    ]
    for path in paths:
        try:
            result = subprocess.run([path, '--version'], 
                                 capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return path
        except:
            pass
    return 'redis-server'


def start_redis_instance(port, cluster_port, dir_path, redis_bin):
    """启动单个Redis实例"""
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
        subprocess.run([redis_bin, conf_file], 
                     capture_output=True, timeout=10)
        time.sleep(1)
        
        # 检查是否启动成功
        node = RedisNode(host='127.0.0.1', port=port)
        if node.ping():
            return True
    except Exception as e:
        print(f"  Failed to start on port {port}: {e}")
    
    return False


def create_cluster(hosts_ports, redis_bin):
    """创建Redis Cluster"""
    # 使用redis-cli创建集群
    hosts = ' '.join([f"127.0.0.1:{p}" for p in hosts_ports])
    
    cmd = f"redis-cli --cluster create {hosts} --cluster-yes --cluster-replicas 1"
    
    try:
        result = subprocess.run(cmd.split(), 
                               capture_output=True, text=True, timeout=60)
        return result.returncode == 0
    except Exception as e:
        print(f"  Failed to create cluster: {e}")
        return False


def simulate_local_cluster(args):
    """在本地模拟Redis Cluster"""
    print_header("Simulating Local Redis Cluster")
    
    redis_bin = args.redis_bin
    if redis_bin == 'redis-server':
        redis_bin = find_redis_bin()
    
    print(f"  Redis binary: {redis_bin}")
    print(f"  Shards: {args.shards}")
    print(f"  Replicas per master: {args.replicas}")
    print(f"  Base port: {args.base_port}")
    
    base_port = args.base_port
    shards = args.shards
    replicas = args.replicas
    
    # 计算总节点数
    # 模式: 每个shard有1个master + replicas个replica
    # 但Cluster模式下replica会共享，所以实际是 shards * (1 + replicas)
    # 但为了简化，我们用标准3主3从模式
    total_nodes = shards * (1 + replicas)
    
    print(f"\n  Total nodes: {total_nodes}")
    
    # 分配端口
    # 前shards个端口作为master，后shards*replicas个作为replica
    master_ports = [base_port + i for i in range(shards)]
    replica_ports = [base_port + shards + i for i in range(shards * replicas)]
    
    all_ports = master_ports + replica_ports
    
    print(f"  Master ports: {master_ports}")
    print(f"  Replica ports: {replica_ports}")
    
    # 检查端口是否已被占用
    print("\n  Checking ports...")
    occupied = []
    for port in all_ports:
        try:
            node = RedisNode(host='127.0.0.1', port=port)
            if node.ping():
                occupied.append(port)
                print(f"    Port {port}: OCCUPIED")
        except:
            print(f"    Port {port}: available")
    
    if occupied:
        print(f"\n  ⚠ Ports {occupied} are already in use!")
        if not confirm_action("Continue anyway (may fail)?"):
            return None
    
    # 启动所有Redis实例
    print("\n  Starting Redis instances...")
    
    for port in all_ports:
        dir_path = f"/tmp/redis_cluster_{port}"
        if start_redis_instance(port, port, dir_path, redis_bin):
            print(f"    ✓ Started on port {port}")
        else:
            print(f"    ✗ Failed to start on port {port}")
    
    # 等待所有实例启动
    print("\n  Waiting for instances to be ready...")
    time.sleep(2)
    
    # 创建集群
    print("\n  Creating cluster...")
    # redis-cli --cluster create 需要所有节点（master+replica），它会自动分配角色
    cluster_hosts = [f"127.0.0.1:{p}" for p in all_ports]

    # 使用redis-cli创建集群
    cmd = [
        'redis-cli', '--cluster', 'create'
    ] + cluster_hosts + [
        '--cluster-yes',
        f'--cluster-replicas', str(replicas)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        print(result.stdout)
        if result.returncode != 0:
            print(f"  Warning: {result.stderr}")
    except Exception as e:
        print(f"  Cluster creation: {e}")
    
    # 等待集群稳定并验证状态为 ok
    print("  Waiting for cluster to be ready...")
    max_wait = 30
    wait_interval = 2
    for i in range(max_wait // wait_interval):
        time.sleep(wait_interval)
        try:
            node = RedisNode(host='127.0.0.1', port=master_ports[0])
            info = get_cluster_info(node)
            state = info.get('cluster_state', '')
            if state == 'ok':
                print(f"    ✓ Cluster state: {state}")
                break
            else:
                print(f"    Waiting... cluster_state={state}")
        except Exception as e:
            print(f"    Waiting... {e}")
    else:
        print("    ⚠ Warning: Cluster state may not be ok")
    
    # 生成配置 - 从实际集群拓扑读取 master-slave 映射
    config = {
        'mode': 'simulate',
        'generated_at': datetime.now().isoformat(),
        'redis_binary': redis_bin,
        'shards': []
    }

    # 从 CLUSTER NODES 读取真实拓扑（redis-cli --cluster create 会做 anti-affinity 优化）
    master_to_slaves = {}  # master_node_id -> [(host, port), ...]
    master_id_to_port = {}  # master_node_id -> port
    try:
        node = RedisNode(host='127.0.0.1', port=master_ports[0])
        nodes_info = node.execute_command('CLUSTER', 'NODES')
        if isinstance(nodes_info, bytes):
            nodes_info = nodes_info.decode('utf-8')
        for line in nodes_info.strip().split('\n'):
            if not line.strip():
                continue
            parts = line.split()
            node_id = parts[0]
            addr = parts[1].split('@')[0]
            host, port_str = addr.rsplit(':', 1)
            port = int(port_str)
            flags = parts[2].split(',')
            master_id = parts[3]  # '-' for masters, master_id for slaves
            if 'master' in flags:
                master_id_to_port[node_id] = port
                master_to_slaves.setdefault(node_id, [])
            elif 'slave' in flags:
                master_to_slaves.setdefault(master_id, []).append((host, port))
    except Exception as e:
        print(f"  Warning: Failed to read cluster topology: {e}")

    for i in range(shards):
        master_port = master_ports[i]

        # 找到这个 master port 对应的 node_id
        master_node_id = None
        for nid, mp in master_id_to_port.items():
            if mp == master_port:
                master_node_id = nid
                break

        # 从实际拓扑获取 slaves
        shard_replicas = []
        if master_node_id and master_node_id in master_to_slaves:
            for idx, (slave_host, slave_port) in enumerate(master_to_slaves[master_node_id]):
                shard_replicas.append({
                    'host': slave_host,
                    'port': slave_port,
                    'region': 'B' if idx == replicas - 1 else 'A'
                })
        else:
            # fallback: sequential assignment
            for j in range(replicas):
                replica_idx = i * replicas + j
                if replica_idx < len(replica_ports):
                    shard_replicas.append({
                        'host': '127.0.0.1',
                        'port': replica_ports[replica_idx],
                        'region': 'B' if j == replicas - 1 else 'A'
                    })

        shard = {
            'shard_index': i,
            'master': {
                'host': '127.0.0.1',
                'port': master_port,
                'current_version': '6.2.x',
                'new_version': '7.2.x'
            },
            'slaves': shard_replicas,
            'new_slaves': [
                {
                    'host': '127.0.0.1',
                    'port': base_port + 100 + i * (replicas + 1) + j,
                    'region': ['A', 'B', 'C'][j] if j < 3 else 'A',
                    'version': '7.2.x'
                }
                for j in range(replicas + 1)
            ]
        }

        config['shards'].append(shard)
    
    # 添加节点配置
    config['nodes'] = []
    for port in all_ports:
        config['nodes'].append({
            'host': '127.0.0.1',
            'port': port,
            'password': ''
        })
    
    # 保存配置
    save_config(config, args.output)
    print(f"\n  ✓ Config saved to: {args.output}")
    
    # 验证集群
    print("\n  Verifying cluster...")
    try:
        node = RedisNode(host='127.0.0.1', port=master_ports[0])
        info = get_cluster_info(node)
        print(f"    Cluster state: {info.get('cluster_state', 'unknown')}")
        print(f"    Cluster nodes: {info.get('cluster_nodes', 'unknown')}")
    except Exception as e:
        print(f"    Warning: {e}")
    
    return config


def collect_cluster_info(nodes_config: dict, args) -> dict:
    """收集真实集群信息"""
    sample = {
        'collected_at': datetime.now().isoformat(),
        'cluster': {},
        'nodes': {},
        'warnings': []
    }
    
    # 选择一个节点获取集群信息
    first_node = nodes_config.get('nodes', [])[0]
    if not first_node:
        print_status("ERROR", "No nodes configured", "FAIL")
        return sample
    
    # 连接第一个节点
    node = RedisNode(
        host=first_node['host'],
        port=first_node.get('port', 6379),
        password=first_node.get('password')
    )
    
    if not node.ping():
        print_status("ERROR", f"Cannot connect to {node}", "FAIL")
        return sample
    
    # 获取集群信息
    print_section("Collecting Cluster Info")
    cluster_info = get_cluster_info(node)
    sample['cluster'] = cluster_info
    print_status("Cluster State", cluster_info.get('cluster_state', 'unknown'))
    print_status("Cluster Slots Assigned", cluster_info.get('cluster_slots_assigned', 'unknown'))
    print_status("Cluster Nodes", cluster_info.get('cluster_nodes', 'unknown'))
    
    # 获取节点信息
    print_section("Collecting Nodes Info")
    cluster_nodes = get_cluster_nodes(node)
    
    # 遍历所有配置的节点
    for node_id, node_info in cluster_nodes.items():
        host = node_info['host']
        port = node_info['port']
        role = node_info['role']
        
        print_section(f"Node: {host}:{port} ({role})")
        
        # 连接节点
        try:
            redis_node = RedisNode(host=host, port=port)
            
            version = get_redis_version(redis_node)
            rdb_version = get_rdb_version(redis_node)
            
            print_status("Redis Version", version)
            print_status("RDB Version", rdb_version)
            
            # 获取复制信息
            if role == 'master':
                info = redis_node.info('replication')
                connected_slaves = info.get('connected_slaves', 0)
                print_status("Connected Slaves", connected_slaves)
            else:
                info = redis_node.info('replication')
                master_link_status = info.get('master_link_status', 'down')
                print_status("Master Link Status", master_link_status)
            
            # 记录节点信息
            sample['nodes'][f"{host}:{port}"] = {
                'node_id': node_id,
                'host': host,
                'port': port,
                'role': role,
                'redis_version': version,
                'rdb_version': rdb_version,
                'master_id': node_info.get('master_id'),
                'flags': node_info.get('flags', [])
            }
            
            # 检查版本一致性
            if '6.' in version:
                sample['nodes'][f"{host}:{port}"]['version_family'] = 'v6'
            elif '7.' in version:
                sample['nodes'][f"{host}:{port}"]['version_family'] = 'v7'
            
            # 版本检查警告
            if sample['nodes'][f"{host}:{port}"]['version_family'] != 'v6':
                sample['warnings'].append(f"Node {host}:{port} is not v6: {version}")
                
        except Exception as e:
            print_status("ERROR", str(e), "FAIL")
            sample['warnings'].append(f"Failed to connect to {host}:{port}: {e}")
    
    return sample


def check_cluster_health(sample: dict) -> bool:
    """检查集群健康状态"""
    print_section("Cluster Health Check")
    
    # 检查集群状态
    cluster_state = sample.get('cluster', {}).get('cluster_state')
    if cluster_state != 'ok':
        print_status("WARNING", f"Cluster state is {cluster_state}", "WARN")
        return False
    
    print_status("Cluster State", cluster_state, "OK")
    
    # 检查节点版本
    print_section("Version Check")
    versions = {}
    for node_key, node_info in sample.get('nodes', {}).items():
        vf = node_info.get('version_family', 'unknown')
        versions[vf] = versions.get(vf, 0) + 1
        print_status(f"Node {node_key}", f"{node_info['redis_version']} ({vf})")
    
    # 检查是否所有节点都是v6
    if versions.get('v6', 0) != len(sample.get('nodes', {})):
        sample['warnings'].append(f"Not all nodes are v6: {versions}")
        print_status("WARNING", f"Found non-v6 nodes: {versions}", "WARN")
    else:
        print_status("All Nodes", "v6.x", "OK")
    
    return True


def generate_upgrade_config(sample: dict, config: dict, args) -> dict:
    """生成升级配置文件"""
    print_section("Generating Upgrade Config")
    
    # 分类节点
    masters = []
    slaves = []
    
    for node_key, node_info in sample.get('nodes', {}).items():
        if node_info.get('role') == 'master':
            masters.append({
                'host': node_info['host'],
                'port': node_info['port'],
                'node_id': node_info.get('node_id'),
                'slaves': []
            })
        else:
            slaves.append({
                'host': node_info['host'],
                'port': node_info['port'],
                'node_id': node_info.get('node_id'),
                'master_host': None,
                'master_port': None
            })
    
    # 为从节点关联主节点
    for node_key, node_info in sample.get('nodes', {}).items():
        master_id = node_info.get('master_id')
        if master_id:
            for master in masters:
                if master['node_id'] == master_id:
                    for slave in slaves:
                        if slave['node_id'] == node_info['node_id']:
                            slave['master_host'] = master['host']
                            slave['master_port'] = master['port']
    
    # 构建升级配置
    upgrade_config = {
        'mode': 'collect',
        'generated_at': datetime.now().isoformat(),
        'shards': [],
        'master_password': config.get('master_password', ''),
        'slave_password': config.get('slave_password', '')
    }
    
    # 每个master为一组
    for idx, master in enumerate(masters):
        shard = {
            'shard_index': idx,
            'master': {
                'host': master['host'],
                'port': master['port'],
                'current_version': '6.2.x',
                'new_version': '7.2.x'
            },
            'slaves': [],
            'new_slaves': []
        }
        
        # 找同master的从节点
        for slave in slaves:
            if (slave.get('master_host') == master['host'] and 
                slave.get('master_port') == master['port']):
                shard['slaves'].append({
                    'host': slave['host'],
                    'port': slave['port'],
                    'current_version': '6.2.x'
                })
        
        # 添加新节点占位符（需要用户填写）
        num_replicas = len(shard['slaves'])
        for i in range(num_replicas):
            shard['new_slaves'].append({
                'host': '',  # 待填写
                'port': 6379,
                'region': 'A' if i % 2 == 0 else 'B',
                'version': '7.2.x'
            })
        
        upgrade_config['shards'].append(shard)
    
    # 保存配置
    save_config(upgrade_config, args.output)
    print_status("Config saved", args.output, "OK")
    
    return upgrade_config


def main():
    args = parse_args()
    
    print_header("Step 0: Prepare Redis Cluster")
    print(f"  Mode: {args.mode}")
    print(f"  Output: {args.output}")
    
    # 检查输出文件是否已存在
    if os.path.exists(args.output) and not args.force:
        print(f"\n  File {args.output} already exists.")
        if not confirm_action("Overwrite?"):
            print("Aborted.")
            sys.exit(1)
    
    if args.mode == 'simulate':
        # 模拟模式
        config = simulate_local_cluster(args)
        if not config:
            print("\n✗ Failed to simulate cluster")
            sys.exit(1)
        
        print_header("Summary")
        print(f"  Total shards: {args.shards}")
        print(f"  Total nodes: {args.shards * (1 + args.replicas)}")
        print(f"  Config saved to: {args.output}")
        
        print("\n  Next steps:")
        print("  1. Edit upgrade_config.json to add new v7 node IPs")
        print("  2. Run: python scripts/pre_upgrade_check.py -c upgrade_config.json")
        
    else:
        # 收集模式
        print(f"\n  Reading nodes from: {args.config}")
        
        config = load_config(args.config)
        if not config:
            print_status("ERROR", f"No configuration found in {args.config}", "FAIL")
            print("\nPlease create a config file with the following format:")
            print("""
{
  "nodes": [
    {"host": "192.168.1.1", "port": 6379, "password": "optional"},
    {"host": "192.168.1.2", "port": 6379, "password": "optional"},
    ...
  ],
  "master_password": "your_password",
  "slave_password": "your_password"
}
""")
            sys.exit(1)
        
        # 收集集群信息
        sample = collect_cluster_info(config, args)
        
        # 检查集群健康
        if not check_cluster_health(sample):
            print("\n" + "="*50)
            print("WARNING: Cluster is not healthy!")
            print("="*50)
            
            if not confirm_action("Continue anyway?"):
                print("Aborted.")
                sys.exit(1)
        
        # 生成升级配置
        upgrade_config = generate_upgrade_config(sample, config, args)
        
        # 打印摘要
        print_header("Summary")
        print(f"  Total nodes: {len(sample.get('nodes', {}))}")
        print(f"  Masters: {sum(1 for n in sample.get('nodes', {}).values() if n.get('role') == 'master')}")
        print(f"  Slaves: {sum(1 for n in sample.get('nodes', {}).values() if n.get('role') == 'slave')}")
        print(f"  Shards: {len(upgrade_config.get('shards', []))}")
        
        if sample.get('warnings'):
            print_section("Warnings")
            for warning in sample['warnings']:
                print_status("WARNING", warning, "WARN")
        
        print("\n" + "="*50)
        print("Step 0 completed!")
        print("="*50)
        print(f"\nNext step: Run pre_upgrade_check.py with {args.output}")
        print("\nNOTE: Please edit upgrade_config.json to add new v7 node IPs in new_slaves")


if __name__ == '__main__':
    main()
