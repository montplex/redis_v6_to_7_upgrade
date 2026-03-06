#!/usr/bin/env python3
"""
Step 5 / Step 9: Redis Client Stress Test - 模拟客户端读写
在failover过程中检测错误，记录错误持续时间和命令数

使用场景:
- Step 5: Failover前压力测试
- Step 9: 回滚后压力测试

测试覆盖:
- String/List/Hash/Set/ZSet/Stream/HLL/Bitmap/Geo 操作
- Lua脚本执行
- Cluster模式MOVED重定向处理
"""

import sys
import os
import time
import argparse
import threading
import random
import string
from datetime import datetime
from collections import defaultdict

try:
    import redis
    from redis.cluster import RedisCluster
except ImportError:
    print("Please install redis-py: pip install redis")
    sys.exit(1)


class StressTestResult:
    """压力测试结果"""
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.total_commands = 0
        self.success_commands = 0
        self.failed_commands = 0
        self.error_periods = []  # [(start_time, end_time, error_count)]
        self.current_error_start = None
        self.current_error_count = 0
        self.lock = threading.Lock()
    
    def record_success(self):
        with self.lock:
            self.success_commands += 1
            self.total_commands += 1
    
    def record_error(self, error_type=None):
        with self.lock:
            self.failed_commands += 1
            self.total_commands += 1
            
            now = time.time()
            if self.current_error_start is None:
                self.current_error_start = now
                self.current_error_count = 1
            else:
                self.current_error_count += 1
    
    def end_error_period(self):
        with self.lock:
            if self.current_error_start is not None:
                self.error_periods.append({
                    'start': self.current_error_start,
                    'end': time.time(),
                    'count': self.current_error_count
                })
                self.current_error_start = None
                self.current_error_count = 0
    
    def get_summary(self):
        with self.lock:
            total_time = 0
            if self.start_time and self.end_time:
                total_time = self.end_time - self.start_time
            
            total_error_time = sum(
                ep['end'] - ep['start'] for ep in self.error_periods
            )
            
            return {
                'total_time': total_time,
                'total_commands': self.total_commands,
                'success_commands': self.success_commands,
                'failed_commands': self.failed_commands,
                'success_rate': (self.success_commands / self.total_commands * 100) 
                               if self.total_commands > 0 else 0,
                'error_periods_count': len(self.error_periods),
                'total_error_time': total_error_time,
                'error_periods': self.error_periods
            }


class RedisStressTest:
    """Redis压力测试客户端"""
    
    def __init__(self, nodes, password=None, qps=1000, key_prefix="test",
                 string_count=1000000, list_count=100000, hash_count=100000,
                 set_count=10000, zset_count=10000, stream_count=1000,
                 hll_count=1000, bitmap_count=1000, geo_count=1000):
        self.nodes = nodes
        self.password = password
        self.qps = qps
        self.key_prefix = key_prefix
        self.running = False
        self.result = StressTestResult()
        self.threads = []
        
        # 数据类型key数量
        self.data_counts = {
            'string': string_count,
            'list': list_count,
            'hash': hash_count,
            'set': set_count,
            'zset': zset_count,
            'stream': stream_count,
            'hll': hll_count,
            'bitmap': bitmap_count,
            'geo': geo_count,
        }
        
        # 连接池
        self.pools = {}
        
        # Lua脚本相关
        self.loaded_scripts = []
        
        # 尝试导入rediscluster (仅支持Cluster模式)
        try:
            from redis.cluster import RedisCluster, ClusterNode
            self.use_cluster = True
            print("  Using RedisCluster client")
        except ImportError:
            print("  ERROR: redis-py-cluster is required. Install with: pip install redis")
            raise ImportError("redis-py-cluster is required for Cluster mode")
    
    def load_scripts(self):
        """加载Lua脚本"""
        print("\n  Loading Lua scripts...")
        try:
            client = self.get_client()
            
            # 定义多个Lua脚本
            scripts = [
                ("return redis.call('get', KEYS[1])", "script_get"),
                ("return redis.call('set', KEYS[1], ARGV[1])", "script_set"),
                ("return redis.call('incr', KEYS[1])", "script_incr"),
                ("return redis.call('del', KEYS[1])", "script_del"),
                ("return redis.call('exists', KEYS[1])", "script_exists"),
                ("""
local key = KEYS[1]
local value = redis.call('get', key)
if not value then
    return nil
end
return value .. '_suffix'
                """, "script_suffix"),
                ("""
local key = KEYS[1]
local n = tonumber(ARGV[1])
local current = tonumber(redis.call('get', key) or 0)
return redis.call('set', key, current + n)
                """, "script_incrby"),
            ]
            
            for script_code, name in scripts:
                sha = client.script_load(script_code)
                self.loaded_scripts.append((sha, name, script_code))
                print(f"    Loaded: {name} (SHA: {sha[:8]}...)")
            
            print(f"  ✓ Loaded {len(self.loaded_scripts)} scripts")
            
        except Exception as e:
            print(f"  ⚠ Failed to load scripts: {e}")
            self.loaded_scripts = []
    
    def test_noscript_fallback(self, client=None):
        """测试 EVALSHA -> NOSCRIPT -> fallback 场景
        
        ⚠️ 重要: 这个测试用于验证脚本缓存丢失后的fallback逻辑
        - 模拟脚本缓存miss (使用不存在的SHA)
        - 验证应用能正确处理NOSCRIPT错误并fallback
        
        Returns:
            dict: 测试结果 {'noscript_detected': bool, 'fallback_success': bool}
        """
        print("\n  Testing EVALSHA/NOSCRIPT fallback scenarios...")
        
        if not client:
            client = self.get_client()
        
        results = {
            'noscript_detected': False,
            'fallback_script_load': False,
            'fallback_eval': False,
            'errors': []
        }
        
        test_key = "test:noscript:stress"
        
        try:
            # 设置测试数据
            client.set(test_key, "test_value")
            
            # 1. 加载一个测试脚本
            lua_script = "return redis.call('get', KEYS[1])"
            script_sha = client.script_load(lua_script)
            
            # 2. 使用有效SHA的EVALSHA（应该成功）
            try:
                result = client.evalsha(script_sha, 1, test_key)
                if result == b'test_value':
                    pass  # 正常
            except Exception as e:
                results['errors'].append(f"EVALSHA success: {e}")
            
            # 3. 使用不存在的SHA（模拟NOSCRIPT场景）
            fake_sha = "0" * 40  # 无效SHA
            try:
                client.evalsha(fake_sha, 1, test_key)
                results['errors'].append("NOSCRIPT not triggered with fake SHA")
            except Exception as e:
                err_str = str(e).upper()
                if 'NOSCRIPT' in err_str:
                    results['noscript_detected'] = True
                results['errors'].append(f"Error: {e}")
            
            # 4. 验证fallback - SCRIPT LOAD
            try:
                new_sha = client.script_load(lua_script)
                result = client.evalsha(new_sha, 1, test_key)
                results['fallback_script_load'] = (result == b'test_value')
            except Exception as e:
                results['errors'].append(f"Fallback SCRIPT LOAD: {e}")
            
            # 5. 验证fallback - EVAL
            try:
                result = client.eval(lua_script, 1, test_key)
                results['fallback_eval'] = (result == b'test_value')
            except Exception as e:
                results['errors'].append(f"Fallback EVAL: {e}")
            
            # 清理
            try:
                client.delete(test_key)
            except:
                pass
            
            # 打印结果
            print(f"    NOSCRIPT detected: {'✓' if results['noscript_detected'] else '✗'}")
            print(f"    Fallback (SCRIPT LOAD): {'✓' if results['fallback_script_load'] else '✗'}")
            print(f"    Fallback (EVAL): {'✓' if results['fallback_eval'] else '✗'}")
            
            if results['errors']:
                for err in results['errors']:
                    print(f"      - {err}")
            
            return results
            
        except Exception as e:
            print(f"    ✗ ERROR in NOSCRIPT test: {e}")
            results['errors'].append(str(e))
            return results
    
    def get_client(self):
        """获取Redis客户端 (Cluster模式)"""
        if not hasattr(self, '_cluster_client') or self._cluster_client is None:
            from redis.cluster import ClusterNode
            startup_nodes = [ClusterNode(n['host'], n['port']) for n in self.nodes]
            self._cluster_client = RedisCluster(
                startup_nodes=startup_nodes,
                decode_responses=False,
                skip_full_coverage_check=True,
                max_connections=30,
                retry_on_timeout=True
            )
        return self._cluster_client
    
    def generate_key(self):
        """生成随机key - 使用与prepare_data.py相同的key格式"""
        # 数据类型前缀（与prepare_data.py保持一致）
        prefixes = [
            ('string', self.data_counts.get('string', 1000000)),
            ('list', self.data_counts.get('list', 100000)),
            ('hash', self.data_counts.get('hash', 100000)),
            ('set', self.data_counts.get('set', 10000)),
            ('zset', self.data_counts.get('zset', 10000)),
            ('stream', self.data_counts.get('stream', 1000)),
            ('hll', self.data_counts.get('hll', 1000)),
            ('bitmap', self.data_counts.get('bitmap', 1000)),
            ('geo', self.data_counts.get('geo', 1000)),
        ]
        
        # 随机选择一个数据类型
        dtype, count = random.choice(prefixes)
        
        # 生成key，范围是 0 到 count-1
        return f"{self.key_prefix}:{dtype}:{random.randint(0, count - 1)}"
    
    def generate_value(self, size=100):
        """生成随机value"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=size))
    
    def do_write(self, client):
        """执行写操作"""
        key = self.generate_key()
        value = self.generate_value()
        try:
            client.set(key, value)
            self.result.record_success()
            return True
        except Exception as e:
            # 对于Cluster模式，可能遇到MOVED错误，尝试从正确的节点重试
            err_str = str(e)
            if 'MOVED' in err_str:
                try:
                    # 简单重试一次
                    client.set(key, value)
                    self.result.record_success()
                    return True
                except:
                    pass
            self.result.record_error(str(e))
            return False
    
    def do_read(self, client):
        """执行读操作"""
        key = self.generate_key()
        try:
            client.get(key)
            self.result.record_success()
            return True
        except Exception as e:
            err_str = str(e)
            if 'MOVED' in err_str:
                try:
                    client.get(key)
                    self.result.record_success()
                    return True
                except:
                    pass
            self.result.record_error(str(e))
            return False
    
    def do_hash_write(self, client):
        """执行Hash写操作"""
        key = self.generate_key()
        try:
            client.hset(key, mapping={'field1': 'value1', 'field2': 'value2'})
            self.result.record_success()
            return True
        except Exception as e:
            self.result.record_error(str(e))
            return False
    
    def do_hash_read(self, client):
        """执行Hash读操作"""
        key = self.generate_key()
        try:
            client.hgetall(key)
            self.result.record_success()
            return True
        except Exception as e:
            self.result.record_error(str(e))
            return False
    
    def do_list_push(self, client):
        """执行List写操作"""
        key = self.generate_key()
        try:
            client.lpush(key, "value")
            self.result.record_success()
            return True
        except Exception as e:
            self.result.record_error(str(e))
            return False
    
    def worker(self, worker_id, ops_per_second):
        """工作线程"""
        # 获取一个客户端
        client = self.get_client()
        
        # 定义每个数据类型的操作
        # 格式: (prefix, range_count, operations_list, weight)
        # operations_list: [(method_name, command_func), ...]
        
        # String: 1000000 keys, 频率最高
        string_ops = [
            ('string:get', lambda c, k: c.get(k)),
            ('string:set', lambda c, k: c.set(k, 'new_value')),
            ('string:getdel', lambda c, k: c.getdel(k)),
            ('string:incr', lambda c, k: c.incr(k + '_counter')),
            ('string:strlen', lambda c, k: c.strlen(k)),
        ]
        
        # List: 100000 keys
        list_ops = [
            ('list:lrange', lambda c, k: c.lrange(k, 0, -1)),
            ('list:llen', lambda c, k: c.llen(k)),
            ('list:lindex', lambda c, k: c.lindex(k, 0)),
            ('list:lpush', lambda c, k: c.lpush(k, 'new_value')),
        ]
        
        # Hash: 100000 keys
        hash_ops = [
            ('hash:hgetall', lambda c, k: c.hgetall(k)),
            ('hash:hget', lambda c, k: c.hget(k, 'field_0')),
            ('hash:hlen', lambda c, k: c.hlen(k)),
            ('hash:hset', lambda c, k: c.hset(k, 'new_field', 'value')),
        ]
        
        # Set: 10000 keys
        set_ops = [
            ('set:smembers', lambda c, k: c.smembers(k)),
            ('set:sismember', lambda c, k: c.sismember(k, 'member_0')),
            ('set:scard', lambda c, k: c.scard(k)),
            ('set:sadd', lambda c, k: c.sadd(k, 'new_member')),
        ]
        
        # ZSet: 10000 keys
        zset_ops = [
            ('zset:zrange', lambda c, k: c.zrange(k, 0, -1)),
            ('zset:zcard', lambda c, k: c.zcard(k)),
            ('zset:zscore', lambda c, k: c.zscore(k, 'member_0')),
            ('zset:zadd', lambda c, k: c.zadd(k, {'new_member': 1.0})),
        ]
        
        # Stream: 1000 keys
        stream_ops = [
            ('stream:xrange', lambda c, k: c.xrange(k)),
            ('stream:xlen', lambda c, k: c.xlen(k)),
            ('stream:xread', lambda c, k: c.xread({k: '0-0'})),
        ]
        
        # HyperLogLog: 1000 keys
        hll_ops = [
            ('hll:pfcount', lambda c, k: c.pfcount(k)),
            ('hll:pfadd', lambda c, k: c.pfadd(k, 'new_element')),
        ]
        
        # Bitmap: 1000 keys
        bitmap_ops = [
            ('bitmap:getbit', lambda c, k: c.getbit(k, 0)),
            ('bitmap:setbit', lambda c, k: c.setbit(k, 0, 1)),
            ('bitmap:bitcount', lambda c, k: c.bitcount(k)),
        ]
        
        # Geospatial: 1000 keys
        geo_ops = [
            ('geo:geopos', lambda c, k: c.geopos(k, 'beijing')),
            ('geo:geodist', lambda c, k: c.geodist(k, 'beijing', 'shanghai')),
            ('geo:georadius', lambda c, k: c.georadius(k, 116, 40, 100, 'km')),
        ]
        
        # Lua Script: 使用已加载的脚本
        script_ops = []
        if self.loaded_scripts:
            for sha, name, script_code in self.loaded_scripts:
                # eval操作
                script_ops.append((f'script:eval:{name}', 
                    lambda c, k, s=script_code: c.eval("return redis.call('get', KEYS[1])", 1, k)))
                # evalsha操作
                script_ops.append((f'script:evalsha:{name}', 
                    lambda c, k, s=sha: c.evalsha(s, 1, k)))
                # noscript模拟（通过EVALSHA with 不存在的SHA）
                # 注意：这会触发NOSCRIPT错误，用于测试fallback逻辑
                fake_sha = "a" * 40  # 不存在的SHA
                script_ops.append((f'script:noscript:{name}',
                    lambda c, k, s=fake_sha: c.evalsha(s, 1, k)))
        
        # 权重：与数据准备的数量成正比
        # string:1M, list:100k, hash:100k, set:10k, zset:10k, stream:1k, hll:1k, bitmap:1k, geo:1k, script:100
        data_types = [
            ('string', 1000000, string_ops),
            ('list', 100000, list_ops),
            ('hash', 100000, hash_ops),
            ('set', 10000, set_ops),
            ('zset', 10000, zset_ops),
            ('stream', 1000, stream_ops),
            ('hll', 1000, hll_ops),
            ('bitmap', 1000, bitmap_ops),
            ('geo', 1000, geo_ops),
        ]
        
        # 如果有加载的脚本，添加到数据列表
        if script_ops:
            # 设置权重为30 (20 for scripts + 10 for noscript模拟)
            data_types.append(('script', 100, script_ops))
        
        # 按权重选择数据类型
        # string约1000，其他按比例
        # script设置权重为20，保证能测试到
        weights = []
        for dtype, count, _ in data_types:
            if dtype == 'script':
                weights.append(20)  # script固定权重
            else:
                weights.append(count // 1000)
        
        interval = 1.0 / ops_per_second if ops_per_second > 0 else 0
        next_time = time.time()
        
        while self.running:
            try:
                # 随机选择数据类型
                dtype, count, ops = random.choices(data_types, weights=weights)[0]
                
                # 随机选择一个key
                key_idx = random.randint(0, count - 1)
                key = f"test:{dtype}:{key_idx:06d}"
                
                # 随机选择该类型的一个操作
                op_name, op_func = random.choice(ops)
                
                # 执行操作
                op_func(client, key)
                
                self.result.record_success()
                
                # 打印操作信息 (每1000个操作打印一次)
                if self.result.total_commands % 1000 == 0:
                    print(f"    [{self.result.total_commands}] {dtype}:{op_name} on {key}")
                
            except Exception as e:
                self.result.record_error(str(e))
            
            # 控制QPS
            next_time += interval
            sleep_time = next_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def start(self):
        """开始压力测试"""
        # 先加载Lua脚本
        self.load_scripts()
        
        self.running = True
        self.result.start_time = time.time()
        
        # 打印初始dbsize
        try:
            client = self.get_client()
            dbsize = client.dbsize()
            print(f"\n  [Before Stress Test] dbsize = {dbsize:,}")
        except:
            pass
        
        # 计算每个线程的QPS
        num_threads = min(10, self.qps // 100 + 1)
        ops_per_thread = self.qps // num_threads
        
        print(f"  Starting stress test with {num_threads} threads, ~{ops_per_thread} ops/sec each")
        
        for i in range(num_threads):
            t = threading.Thread(target=self.worker, args=(i, ops_per_thread))
            t.daemon = True
            t.start()
            self.threads.append(t)
    
    def stop(self):
        """停止压力测试"""
        self.running = False
        self.result.end_time = time.time()
        self.result.end_error_period()
        
        # 打印结束dbsize
        try:
            client = self.get_client()
            dbsize = client.dbsize()
            print(f"\n  [After Stress Test] dbsize = {dbsize:,}")
        except:
            pass
        
        # 等待所有线程结束
        for t in self.threads:
            t.join(timeout=2)
    
    def get_status(self):
        """获取当前状态"""
        summary = self.result.get_summary()
        elapsed = time.time() - self.result.start_time if self.result.start_time else 0
        
        return {
            'running': self.running,
            'elapsed': elapsed,
            'total_commands': summary['total_commands'],
            'success': summary['success_commands'],
            'failed': summary['failed_commands'],
            'success_rate': summary['success_rate'],
            'error_periods': len(self.result.error_periods)
        }


def parse_args():
    parser = argparse.ArgumentParser(
        description="Redis Client Stress Test - 模拟客户端读写"
    )
    parser.add_argument(
        '--nodes', '-n',
        help='节点列表，格式: host:port,host:port,...'
    )
    parser.add_argument(
        '--config', '-c',
        help='配置文件路径'
    )
    parser.add_argument(
        '--qps', '-q',
        type=int,
        default=1000,
        help='目标QPS (default: 1000)'
    )
    parser.add_argument(
        '--duration', '-d',
        type=int,
        default=300,
        help='测试持续时间，秒 (default: 300)'
    )
    parser.add_argument(
        '--password', '-p',
        help='Redis密码'
    )
    parser.add_argument(
        '--key-prefix', '-k',
        default='test',
        help='key前缀 (default: test)'
    )
    parser.add_argument(
        '--string', '-s',
        type=int,
        default=1000000,
        help='String key数量 (default: 1000000)'
    )
    parser.add_argument(
        '--list', '-l',
        type=int,
        default=100000,
        help='List key数量 (default: 100000)'
    )
    parser.add_argument(
        '--hash',
        type=int,
        default=100000,
        help='Hash key数量 (default: 100000)'
    )
    parser.add_argument(
        '--set',
        type=int,
        default=10000,
        help='Set key数量 (default: 10000)'
    )
    parser.add_argument(
        '--zset',
        type=int,
        default=10000,
        help='ZSet key数量 (default: 10000)'
    )
    parser.add_argument(
        '--stream',
        type=int,
        default=1000,
        help='Stream key数量 (default: 1000)'
    )
    parser.add_argument(
        '--hll',
        type=int,
        default=1000,
        help='HyperLogLog key数量 (default: 1000)'
    )
    parser.add_argument(
        '--bitmap',
        type=int,
        default=1000,
        help='Bitmap key数量 (default: 1000)'
    )
    parser.add_argument(
        '--geo',
        type=int,
        default=1000,
        help='Geo key数量 (default: 1000)'
    )
    parser.add_argument(
        '--output', '-o',
        default='stress_test_result.json',
        help='输出结果文件'
    )
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='交互模式：启动后等待用户按键开始failover'
    )
    parser.add_argument(
        '--verify-noscript',
        action='store_true',
        help='运行EVALSHA/NOSCRIPT验证测试（不执行压力测试）'
    )
    return parser.parse_args()


def load_config(config_file):
    """从配置文件加载节点"""
    import json
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        nodes = []
        for shard in config.get('shards', []):
            # 添加master
            master = shard.get('master', {})
            if master.get('host'):
                nodes.append({
                    'host': master['host'],
                    'port': master.get('port', 6379)
                })
            
            # 添加slaves
            for slave in shard.get('slaves', []):
                if slave.get('host'):
                    nodes.append({
                        'host': slave['host'],
                        'port': slave.get('port', 6379)
                    })
        
        return nodes
    except Exception as e:
        print(f"Error loading config: {e}")
        return []


def main():
    args = parse_args()
    
    print("=" * 60)
    print("  Redis Client Stress Test")
    print("  模拟客户端在failover期间的读写")
    print("=" * 60)
    
    # 获取节点列表
    nodes = []
    
    if args.config:
        nodes = load_config(args.config)
        print(f"  Loaded {len(nodes)} nodes from config")
    elif args.nodes:
        for node in args.nodes.split(','):
            host, port = node.strip().rsplit(':', 1)
            nodes.append({'host': host, 'port': int(port)})
        print(f"  Using {len(nodes)} nodes from command line")
    else:
        print("  Error: Please specify --nodes or --config")
        sys.exit(1)
    
    if not nodes:
        print("  Error: No nodes available")
        sys.exit(1)
    
    print(f"  Target QPS: {args.qps}")
    print(f"  Duration: {args.duration}s")
    print(f"  Key prefix: {args.key_prefix}")
    print(f"  Data counts:")
    print(f"    string: {args.string:,}")
    print(f"    list: {args.list:,}")
    print(f"    hash: {args.hash:,}")
    print(f"    set: {args.set:,}")
    print(f"    zset: {args.zset:,}")
    print(f"    stream: {args.stream:,}")
    print(f"    hll: {args.hll:,}")
    print(f"    bitmap: {args.bitmap:,}")
    print(f"    geo: {args.geo:,}")
    
    # 创建压力测试实例
    test = RedisStressTest(
        nodes=nodes,
        password=args.password,
        qps=args.qps,
        key_prefix=args.key_prefix,
        string_count=args.string,
        list_count=args.list,
        hash_count=args.hash,
        set_count=args.set,
        zset_count=args.zset,
        stream_count=args.stream,
        hll_count=args.hll,
        bitmap_count=args.bitmap,
        geo_count=args.geo
    )
    
    # ⚠️ 重要: 如果指定 --verify-noscript，则只运行 NOSCRIPT 验证测试
    if args.verify_noscript:
        print("\n" + "=" * 60)
        print("  Running EVALSHA/NOSCRIPT Verification")
        print("  验证脚本缓存miss场景")
        print("=" * 60 + "\n")
        
        test = RedisStressTest(
            nodes=nodes,
            password=args.password,
            qps=100,
            key_prefix=args.key_prefix,
            string_count=args.string,
            list_count=args.list,
            hash_count=args.hash,
            set_count=args.set,
            zset_count=args.zset,
            stream_count=args.stream,
            hll_count=args.hll,
            bitmap_count=args.bitmap,
            geo_count=args.geo
        )
        
        # 运行 NOSCRIPT 验证
        results = test.test_noscript_fallback()
        
        print("\n" + "=" * 60)
        if results.get('noscript_detected') and results.get('fallback_script_load') and results.get('fallback_eval'):
            print("  ✓ PASS - EVALSHA/NOSCRIPT verification passed")
        else:
            print("  ✗ WARNING - Some checks failed")
        print("=" * 60)
        return
    
    # 交互模式
    if args.interactive:
        print("\n" + "=" * 60)
        print("  Press ENTER to START test...")
        input()
    
    # 开始测试
    print("\n" + "=" * 60)
    print("  Starting stress test...")
    print("  (Press Ctrl+C to stop)")
    print("=" * 60 + "\n")
    
    test.start()
    
    try:
        # 持续运行
        start_time = time.time()
        last_report = start_time
        
        while True:
            time.sleep(1)
            
            status = test.get_status()
            elapsed = time.time() - start_time
            
            # 每10秒报告一次
            if int(elapsed) % 10 == 0 and int(last_report) != int(elapsed):
                print(f"  [{int(elapsed)}s] "
                      f"cmds={status['total_commands']}, "
                      f"success={status['success']}, "
                      f"failed={status['failed']}, "
                      f"rate={status['success_rate']:.1f}%, "
                      f"errors={status['error_periods']}")
                last_report = elapsed
            
            # 检查是否达到持续时间
            if args.duration > 0 and elapsed >= args.duration:
                break
                
    except KeyboardInterrupt:
        print("\n\n  Stopping test...")
    
    # 停止测试
    test.stop()
    
    # 输出结果
    print("\n" + "=" * 60)
    print("  Test Results")
    print("=" * 60)
    
    summary = test.result.get_summary()
    
    print(f"\n  Total time: {summary['total_time']:.2f}s")
    print(f"  Total commands: {summary['total_commands']}")
    print(f"  Success: {summary['success_commands']}")
    print(f"  Failed: {summary['failed_commands']}")
    print(f"  Success rate: {summary['success_rate']:.2f}%")
    
    print(f"\n  Error periods: {summary['error_periods_count']}")
    print(f"  Total error time: {summary['total_error_time']:.2f}s")
    
    if summary['error_periods']:
        print("\n  Error period details:")
        for i, ep in enumerate(summary['error_periods'], 1):
            duration = ep['end'] - ep['start']
            print(f"    [{i}] {duration:.2f}s, {ep['count']} errors")
    
    # 保存结果
    import json
    result_data = {
        'test_time': datetime.now().isoformat(),
        'config': {
            'nodes': nodes,
            'qps': args.qps,
            'duration': args.duration
        },
        'summary': summary
    }
    
    with open(args.output, 'w') as f:
        json.dump(result_data, f, indent=2)
    
    print(f"\n  Results saved to: {args.output}")
    
    # 关键指标
    print("\n" + "=" * 60)
    print("  KEY METRICS FOR FAILOVER TEST")
    print("=" * 60)
    print(f"  Error duration: {summary['total_error_time']:.2f}s")
    print(f"  Error count: {summary['failed_commands']}")
    print(f"  Error periods: {summary['error_periods_count']}")
    
    if summary['error_periods']:
        max_error_duration = max(
            ep['end'] - ep['start'] for ep in summary['error_periods']
        )
        print(f"  Max error duration: {max_error_duration:.2f}s")
    
    print("\n" + "=" * 60)
    if summary['success_rate'] >= 95.0:
        print("  ✓ PASS - Stress test passed (success rate >= 95%)")
    else:
        print("  ✗ FAIL - Stress test failed (success rate < 95%)")
    print("=" * 60)


if __name__ == '__main__':
    main()
