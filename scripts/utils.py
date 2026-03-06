#!/usr/bin/env python3
"""
Redis Upgrade Utils - 公共工具函数
"""

import redis
import time
import json
import sys
from typing import Dict, List, Optional, Tuple, Any


class RedisNode:
    """Redis节点"""
    def __init__(self, host: str, port: int = 6379, password: str = None):
        self.host = host
        self.port = port
        self.password = password
        self._conn = None
    
    def connect(self) -> redis.Redis:
        """连接到Redis节点"""
        if self._conn is None:
            self._conn = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                decode_responses=False
            )
        return self._conn
    
    def ping(self) -> bool:
        """检查节点是否存活"""
        try:
            r = self.connect()
            return r.ping()
        except Exception as e:
            return False
    
    def info(self, section: str = None) -> Dict:
        """获取节点info"""
        try:
            r = self.connect()
            return r.info(section)
        except Exception as e:
            return {}
    
    def role(self) -> Dict:
        """获取节点角色"""
        try:
            r = self.connect()
            return r.info('replication')
        except Exception as e:
            return {}
    
    def execute_command(self, *args) -> Any:
        """执行Redis命令"""
        try:
            r = self.connect()
            return r.execute_command(*args)
        except Exception as e:
            raise Exception(f"Command {' '.join(args)} failed: {e}")
    
    def __repr__(self):
        return f"RedisNode({self.host}:{self.port})"


def print_header(title: str):
    """打印标题"""
    width = 80
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def print_section(title: str):
    """打印章节标题"""
    print(f"\n--- {title} ---")


def print_status(label: str, value: Any, status: str = "OK"):
    """打印状态信息"""
    status_icon = {
        "OK": "\033[92m✓\033[0m",
        "WARN": "\033[93m⚠\033[0m",
        "FAIL": "\033[91m✗\033[0m",
        "INFO": "\033[94mℹ\033[0m"
    }
    icon = status_icon.get(status, "")
    print(f"  {icon} {label}: {value}")


def print_expect(label: str, expected: str, actual: str = None):
    """打印期望值提示"""
    if actual is not None:
        print(f"  → EXPECT: {label} = {expected}")
        print(f"    ACTUAL: {actual}")
    else:
        print(f"  → EXPECT: {label} = {expected}")


def get_redis_version(node: RedisNode) -> str:
    """获取Redis版本"""
    info = node.info()
    return info.get('redis_version', 'unknown')


def get_rdb_version(node: RedisNode) -> int:
    """获取RDB版本"""
    info = node.info('persistence')
    return info.get('rdb_version', 0)


def check_node_health(node: RedisNode) -> Dict:
    """检查节点健康状态"""
    result = {
        'alive': False,
        'version': None,
        'role': None,
        'cluster_state': None,
        'errors': []
    }
    
    try:
        if not node.ping():
            result['errors'].append("Node not responding to PING")
            return result
        
        info = node.info()
        result['alive'] = True
        result['version'] = info.get('redis_version', 'unknown')
        result['role'] = info.get('role', 'unknown')
        
        # 检查cluster状态
        try:
            cluster_info = node.info('cluster')
            result['cluster_state'] = cluster_info.get('cluster_state', 'unknown')
        except:
            result['cluster_state'] = 'not_enabled'
        
    except Exception as e:
        result['errors'].append(str(e))
    
    return result


def wait_for_replication(master: RedisNode, slave: RedisNode, 
                         timeout: int = 60, interval: int = 2) -> bool:
    """等待从节点复制追平主节点
    
    Args:
        master: 主节点
        slave: 从节点
        timeout: 超时时间(秒)
        interval: 检查间隔(秒)
    
    Returns:
        bool: 是否追平
    """
    print(f"  Waiting for replication catchup (timeout: {timeout}s)...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            master_info = master.info('replication')
            slave_info = slave.info('replication')
            
            master_offset = master_info.get('master_repl_offset', 0)
            slave_offset = slave_info.get('slave_repl_offset', 0)
            slave_status = slave_info.get('master_link_status', 'down')
            
            # 检查连接状态
            if slave_status != 'up':
                print(f"    Status: {slave_status}, waiting...")
                time.sleep(interval)
                continue
            
            # 检查offset差距
            offset_diff = abs(master_offset - slave_offset)
            if offset_diff < 1024:  # 1KB以内视为追平
                print(f"    ✓ Caught up! master_offset={master_offset}, slave_offset={slave_offset}")
                return True
            
            print(f"    Syncing: master={master_offset}, slave={slave_offset}, diff={offset_diff}")
            
        except Exception as e:
            print(f"    Error: {e}")
        
        time.sleep(interval)
    
    print(f"    ✗ Timeout after {timeout}s, replication not caught up")
    return False


def verify_replication_status(master: RedisNode, slave: RedisNode) -> Dict:
    """验证复制状态
    
    Returns:
        dict: {
            'connected': bool,
            'offset_match': bool,
            'delay_ms': int,
            'details': {}
        }
    """
    result = {
        'connected': False,
        'offset_match': False,
        'delay_ms': 0,
        'details': {}
    }
    
    try:
        master_info = master.info('replication')
        slave_info = slave.info('replication')
        
        master_offset = master_info.get('master_repl_offset', 0)
        slave_offset = slave_info.get('slave_repl_offset', 0)
        slave_status = slave_info.get('master_link_status', 'down')
        
        result['connected'] = (slave_status == 'up')
        result['offset_match'] = (abs(master_offset - slave_offset) < 1024)
        result['delay_ms'] = abs(master_offset - slave_offset)
        result['details'] = {
            'master_offset': master_offset,
            'slave_offset': slave_offset,
            'master_link_status': slave_status
        }
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


def get_cluster_nodes(node: RedisNode) -> Dict:
    """获取集群节点信息
    
    Returns:
        dict: {node_id: {host, port, role, master_id, ...}}
    """
    try:
        result = node.execute_command('CLUSTER', 'NODES')
        if isinstance(result, bytes):
            result = result.decode('utf-8')
        
        nodes = {}
        
        for line in result.split('\n'):
            if not line.strip():
                continue
            
            parts = line.split()
            node_id = parts[0]
            addr_part = parts[1]
            
            # 解析地址
            if '@' in addr_part:
                addr = addr_part.split('@')[0]
            else:
                addr = addr_part
            
            # 解析角色和状态
            flags = parts[2].split(',')
            role = 'master' if 'master' in flags else 'slave'
            master_id = parts[3] if len(parts) > 3 and parts[3] != '-' else None
            
            # host:port
            if ':' in addr:
                host, port = addr.rsplit(':', 1)
                port = int(port)
            else:
                host = addr
                port = 6379
            
            nodes[node_id] = {
                'node_id': node_id,
                'host': host,
                'port': port,
                'role': role,
                'master_id': master_id,
                'flags': flags
            }
        
        return nodes
        
    except Exception as e:
        print(f"Error getting cluster nodes: {e}")
        return {}


def get_cluster_info(node: RedisNode) -> Dict:
    """获取集群信息"""
    try:
        result = node.execute_command('CLUSTER', 'INFO')
        if isinstance(result, bytes):
            result = result.decode('utf-8')
        
        info = {}
        for line in result.split('\n'):
            if ':' in line:
                key, value = line.strip().split(':', 1)
                info[key] = value
        return info
    except Exception as e:
        return {}


def check_replication_buffers(master: RedisNode) -> Dict:
    """检查复制缓冲区配置"""
    result = {
        'current': {},
        'recommended': {
            'replica': '512MB 64MB 60'
        }
    }
    
    try:
        config = master.info('config')
        result['current']['client_output_buffer_limit_replica'] = config.get('client-output-buffer-limit replica', 'N/A')
    except:
        pass
    
    return result


def verify_command_compatibility(node: RedisNode) -> Dict:
    """验证命令兼容性"""
    results = {}
    
    try:
        r = node.connect()
        
        # 测试 SET with GET parameter
        r.set("test:get", "old_value")
        result = r.set("test:get", "new_value", get=True)
        results['SET_GET'] = {
            'supported': result is not None,
            'value': result.decode() if result else None
        }
        r.delete("test:get")
        
        # 测试 STREAM
        try:
            r.xadd("test_stream", {"field": "value"})
            r.xrange("test_stream")
            r.delete("test_stream")
            results['STREAM'] = {'supported': True}
        except:
            results['STREAM'] = {'supported': False}
            
    except Exception as e:
        results['error'] = str(e)
    
    return results


V6_V7_CONFIG_DIFF = {
    'cluster-allow-reads-when-down': {'v6': 'yes', 'v7': 'no', 'impact': 'v7默认禁止读'},
    'cluster-require-full-coverage': {'v6': 'yes', 'v7': 'no', 'impact': 'v7默认部分slot不可用仍可读'},
    'active-expire-effort': {'v6': '1', 'v7': '8', 'impact': 'v7更积极清理过期key'},
    'lazyfree-lazy-expire': {'v6': 'no', 'v7': 'yes', 'impact': 'v7异步删除过期key'},
    'lazyfree-lazy-eviction': {'v6': 'no', 'v7': 'yes', 'impact': 'v7异步淘汰key'},
    'lazyfree-lazy-server-del': {'v6': 'no', 'v7': 'yes', 'impact': 'v7异步删除key'},
    'replica-ignore-maxmemory': {'v6': 'no', 'v7': 'yes', 'impact': '从节点不执行淘汰'},
}


def verify_v6_v7_config_diff(node: RedisNode) -> Dict:
    """验证 v6/v7 配置差异
    
    检查 design.md 2.1 节要求的配置差异
    """
    results = {}
    
    try:
        r = node.connect()
        
        for param, info in V6_V7_CONFIG_DIFF.items():
            try:
                value = r.config_get(parameter=param).get(param, '')
                results[param] = {
                    'current': value,
                    'v6_default': info['v6'],
                    'v7_default': info['v7'],
                    'impact': info['impact'],
                    'is_v7_default': value == info['v7'],
                    'warning': value != info['v6'] and value != info['v7']
                }
            except Exception as e:
                results[param] = {'error': str(e)}
        
    except Exception as e:
        results['error'] = str(e)
    
    return results


def verify_data_encoding(node: RedisNode) -> Dict:
    """验证数据结构编码"""
    results = {}
    
    try:
        r = node.connect()
        
        # 测试 HASH 编码
        r.delete("test:hash")
        for i in range(520):
            r.hset("test:hash", f"key{i}", f"value{i}")
        encoding = r.object("encoding", "test:hash")
        results['HASH_ENCODING'] = encoding
        r.delete("test:hash")
        
        # 测试 LIST 编码
        r.delete("test:list")
        for i in range(1000):
            r.lpush("test:list", f"value{i}")
        encoding = r.object("encoding", "test:list")
        results['LIST_ENCODING'] = encoding
        r.delete("test:list")
        
        # 测试 ZSET 编码
        r.delete("test:zset")
        for i in range(130):
            r.zadd("test:zset", {f"member{i}": i})
        encoding = r.object("encoding", "test:zset")
        results['ZSET_ENCODING'] = encoding
        r.delete("test:zset")
        
    except Exception as e:
        results['error'] = str(e)
    
    return results


def load_config(config_file: str) -> Dict:
    """加载配置文件"""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing config file: {e}")
        return {}


def save_config(config: Dict, config_file: str):
    """保存配置文件"""
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)


def confirm_action(prompt: str, auto_continue: bool = False) -> bool:
    """确认操作"""
    if auto_continue:
        print(f"\n{prompt}")
        print("  Type 'yes' to confirm: y (auto-confirmed)")
        return True
    print(f"\n{prompt}")
    response = input("  Type 'yes' to confirm: ").strip().lower()
    return response == 'yes'
