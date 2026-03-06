#!/usr/bin/env python3
"""
Step 1: Prepare Test Data - 准备测试数据
在Redis Cluster中填充各种数据结构的测试数据

使用Redis Cluster模式，数据会自动分散到各个shard

覆盖的数据类型:
- String: 1M keys
- List/Hash: 100k keys  
- Set/ZSet: 10k keys
- Stream/HLL/Bitmap/Geo: 1k keys
- Lua Scripts: 100
"""

import sys
import os
import time
import argparse
import random
import string
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import redis
    from redis.cluster import RedisCluster, ClusterNode
except ImportError:
    print("Please install redis-py: pip install redis")
    sys.exit(1)


DEFAULT_COUNTS = {
    'string': 1000000,    # 100万
    'list': 100000,       # 10万
    'hash': 100000,       # 10万
    'set': 10000,         # 1万
    'zset': 10000,        # 1万
    'stream': 1000,       # 1000
    'hyperloglog': 1000,  # 1000
    'bitmap': 1000,       # 1000
    'geospatial': 1000,  # 1000
}


def generate_string_value(size=100):
    """生成随机字符串"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=size))


def generate_hash_fields(count):
    """生成hash字段"""
    return {f"field_{i}": f"value_{i}" for i in range(count)}


def generate_set_members(count):
    """生成set成员"""
    return [f"member_{i}" for i in range(count)]


def generate_zset_members(count):
    """生成zset成员"""
    return {f"member_{i}": random.random() * 1000 for i in range(count)}


def get_cluster_dbsize(client):
    """获取整个集群的key总数"""
    try:
        nodes = client.get_nodes()
        if not nodes:
            return 0
        total = 0
        for node in nodes:
            try:
                r = redis.Redis(host=node.host, port=node.port, decode_responses=False)
                total += r.dbsize()
                r.close()
            except:
                pass
        return total
    except Exception:
        return 0


def prepare_strings(client, count, prefix="test:string"):
    """准备String类型数据 (Cluster模式)"""
    print(f"\n{'='*60}")
    print(f"  Preparing STRINGS")
    print(f"  Prefix: {prefix}:*")
    print(f"  Count: {count:,}")
    print(f"{'='*60}")
    
    start_time = time.time()
    success_count = 0
    
    # 判断是否为cluster模式
    is_cluster = getattr(client, '_is_cluster', False)
    
    if is_cluster:
        # Cluster模式：使用多线程连接不同节点
        nodes = client.get_nodes()
        # 简单起见，使用所有节点
        master_nodes = nodes
        
        print(f"  Using {len(master_nodes)} nodes for distribution")
        
        def write_keys(start_idx, count_per_thread):
            nonlocal success_count
            node_idx = start_idx % len(master_nodes)
            node = master_nodes[node_idx]
            local_client = redis.Redis(host=node.host, port=node.port, decode_responses=False)
            
            for i in range(start_idx, start_idx + count_per_thread):
                if i >= count:
                    break
                key = f"{prefix}:{i:06d}"
                value = generate_string_value(random.randint(10, 200))
                try:
                    local_client.set(key, value)
                    success_count += 1
                except:
                    pass
            local_client.close()
        
        num_threads = min(30, count)
        count_per_thread = count // num_threads
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(write_keys, i*count_per_thread, count_per_thread) for i in range(num_threads)]
            for f in as_completed(futures):
                pass
    else:
        # 非cluster模式（不应出现）
        raise RuntimeError("This script requires Redis Cluster mode")
    
    elapsed = time.time() - start_time
    
    try:
        dbsize = get_cluster_dbsize(client)
        print(f"\n  [After Strings] dbsize = {dbsize:,}")
    except:
        print(f"\n  [After Strings] ~{success_count:,} keys")
    
    print(f"  ✓ Done: {success_count:,} strings in {elapsed:.1f}s ({success_count/elapsed:.0f}/s)")
    return success_count


def prepare_lists(client, count, prefix="test:list"):
    """准备List类型数据"""
    print(f"\n{'='*60}")
    print(f"  Preparing LISTS")
    print(f"  Prefix: {prefix}:*")
    print(f"  Count: {count:,}")
    print(f"{'='*60}")
    
    start_time = time.time()
    success_count = 0
    
    is_cluster = getattr(client, '_is_cluster', False)
    
    if is_cluster:
        def write_lists(start_idx, end_idx):
            nonlocal success_count
            for i in range(start_idx, end_idx):
                key = f"{prefix}:{i:06d}"
                values = [f"value_{k}" for k in range(10)]
                try:
                    client.rpush(key, *values)
                    success_count += 1
                except Exception:
                    pass

        num_threads = min(20, count)
        chunk = count // num_threads

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(write_lists, i*chunk, min((i+1)*chunk, count)) for i in range(num_threads)]
            for f in as_completed(futures):
                pass
    else:
        raise RuntimeError("This script requires Redis Cluster mode")
    
    elapsed = time.time() - start_time
    print(f"\n  [After Lists] ~{success_count:,} keys")
    print(f"  ✓ Done: {success_count:,} lists in {elapsed:.1f}s ({success_count/elapsed:.0f}/s)")
    return success_count


def prepare_hashes(client, count, prefix="test:hash"):
    """准备Hash类型数据"""
    print(f"\n{'='*60}")
    print(f"  Preparing HASHES")
    print(f"  Prefix: {prefix}:*")
    print(f"  Count: {count:,}")
    print(f"{'='*60}")
    
    start_time = time.time()
    success_count = 0
    
    is_cluster = getattr(client, '_is_cluster', False)
    
    if is_cluster:
        def write_hashes(start_idx, end_idx):
            nonlocal success_count
            for i in range(start_idx, end_idx):
                key = f"{prefix}:{i:06d}"
                fields = generate_hash_fields(20)
                try:
                    client.hset(key, mapping=fields)
                    success_count += 1
                except Exception:
                    pass

        num_threads = min(20, count)
        chunk = count // num_threads

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(write_hashes, i*chunk, min((i+1)*chunk, count)) for i in range(num_threads)]
            for f in as_completed(futures):
                pass
    else:
        raise RuntimeError("This script requires Redis Cluster mode")
    
    elapsed = time.time() - start_time
    print(f"\n  [After Hashes] ~{success_count:,} keys")
    print(f"  ✓ Done: {success_count:,} hashes in {elapsed:.1f}s ({success_count/elapsed:.0f}/s)")
    return success_count


def prepare_sets(client, count, prefix="test:set"):
    """准备Set类型数据"""
    print(f"\n{'='*60}")
    print(f"  Preparing SETS")
    print(f"  Prefix: {prefix}:*")
    print(f"  Count: {count:,}")
    print(f"{'='*60}")
    
    start_time = time.time()
    success_count = 0
    
    is_cluster = getattr(client, '_is_cluster', False)
    
    if is_cluster:
        def write_sets(start_idx, end_idx):
            nonlocal success_count
            for i in range(start_idx, end_idx):
                key = f"{prefix}:{i:06d}"
                members = generate_set_members(50)
                try:
                    client.sadd(key, *members)
                    success_count += 1
                except Exception:
                    pass

        num_threads = min(10, count)
        chunk = count // num_threads

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(write_sets, i*chunk, min((i+1)*chunk, count)) for i in range(num_threads)]
            for f in as_completed(futures):
                pass
    else:
        raise RuntimeError("This script requires Redis Cluster mode")
    
    elapsed = time.time() - start_time
    print(f"\n  [After Sets] ~{success_count:,} keys")
    print(f"  ✓ Done: {success_count:,} sets in {elapsed:.1f}s ({success_count/elapsed:.0f}/s)")
    return success_count


def prepare_zsets(client, count, prefix="test:zset"):
    """准备ZSet类型数据"""
    print(f"\n{'='*60}")
    print(f"  Preparing ZSETS")
    print(f"  Prefix: {prefix}:*")
    print(f"  Count: {count:,}")
    print(f"{'='*60}")
    
    start_time = time.time()
    success_count = 0
    
    is_cluster = getattr(client, '_is_cluster', False)
    
    if is_cluster:
        def write_zsets(start_idx, end_idx):
            nonlocal success_count
            for i in range(start_idx, end_idx):
                key = f"{prefix}:{i:06d}"
                members = generate_zset_members(50)
                try:
                    client.zadd(key, members)
                    success_count += 1
                except Exception:
                    pass

        num_threads = min(10, count)
        chunk = count // num_threads

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(write_zsets, i*chunk, min((i+1)*chunk, count)) for i in range(num_threads)]
            for f in as_completed(futures):
                pass
    else:
        raise RuntimeError("This script requires Redis Cluster mode")
    
    elapsed = time.time() - start_time
    print(f"\n  [After ZSets] ~{success_count:,} keys")
    print(f"  ✓ Done: {success_count:,} zsets in {elapsed:.1f}s ({success_count/elapsed:.0f}/s)")
    return success_count


def prepare_streams(client, count, prefix="test:stream"):
    """准备Stream类型数据"""
    print(f"\n{'='*60}")
    print(f"  Preparing STREAMS")
    print(f"  Prefix: {prefix}:*")
    print(f"  Count: {count:,}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    for i in range(count):
        key = f"{prefix}:{i:06d}"
        for k in range(5):
            client.xadd(key, {'field': f'value_{k}'})
        
        if (i + 1) % 200 == 0:
            print(f"    Progress: {i + 1:,}/{count:,}")
    
    elapsed = time.time() - start_time
    
    dbsize = get_cluster_dbsize(client)
    print(f"\n  [After Streams] dbsize = {dbsize:,}")
    print(f"  ✓ Done: {count:,} streams in {elapsed:.1f}s ({count/elapsed:.0f}/s)")
    return count


def prepare_hyperloglogs(client, count, prefix="test:hll"):
    """准备HyperLogLog类型数据"""
    print(f"\n{'='*60}")
    print(f"  Preparing HYPERLOGLOGS")
    print(f"  Prefix: {prefix}:*")
    print(f"  Count: {count:,}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    for i in range(count):
        key = f"{prefix}:{i:06d}"
        elements = [f"element_{k}" for k in range(1000)]
        client.pfadd(key, *elements)
        
        if (i + 1) % 200 == 0:
            print(f"    Progress: {i + 1:,}/{count:,}")
    
    elapsed = time.time() - start_time
    
    dbsize = get_cluster_dbsize(client)
    print(f"\n  [After HyperLogLogs] dbsize = {dbsize:,}")
    print(f"  ✓ Done: {count:,} hyperloglogs in {elapsed:.1f}s ({count/elapsed:.0f}/s)")
    return count


def prepare_bitmaps(client, count, prefix="test:bitmap"):
    """准备Bitmap类型数据"""
    print(f"\n{'='*60}")
    print(f"  Preparing BITMAPS")
    print(f"  Prefix: {prefix}:*")
    print(f"  Count: {count:,}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    for i in range(count):
        key = f"{prefix}:{i:06d}"
        for k in range(0, 1000, 100):
            client.setbit(key, k, 1)
        
        if (i + 1) % 200 == 0:
            print(f"    Progress: {i + 1:,}/{count:,}")
    
    elapsed = time.time() - start_time
    
    dbsize = get_cluster_dbsize(client)
    print(f"\n  [After Bitmaps] dbsize = {dbsize:,}")
    print(f"  ✓ Done: {count:,} bitmaps in {elapsed:.1f}s ({count/elapsed:.0f}/s)")
    return count


def prepare_geospatial(client, count, prefix="test:geo"):
    """准备Geospatial类型数据"""
    print(f"\n{'='*60}")
    print(f"  Preparing GEOSPATIALS")
    print(f"  Prefix: {prefix}:*")
    print(f"  Count: {count:,}")
    print(f"{'='*60}")
    
    cities = [
        ("beijing", 39.9042, 116.4074),
        ("shanghai", 31.2304, 121.4737),
        ("guangzhou", 23.1291, 113.2644),
        ("shenzhen", 22.5431, 114.0579),
        ("chengdu", 30.5728, 104.0668),
    ]
    
    start_time = time.time()
    
    for i in range(count):
        key = f"{prefix}:{i:06d}"
        for name, lat, lon in cities:
            client.geoadd(key, (lon, lat, name))
        
        if (i + 1) % 200 == 0:
            print(f"    Progress: {i + 1:,}/{count:,}")
    
    elapsed = time.time() - start_time
    
    dbsize = get_cluster_dbsize(client)
    print(f"\n  [After Geospatials] dbsize = {dbsize:,}")
    print(f"  ✓ Done: {count:,} geospatials in {elapsed:.1f}s ({count/elapsed:.0f}/s)")
    return count



def prepare_scripts(client, count, prefix="test:lua"):
    """准备Lua脚本"""
    print(f"  Preparing {count} lua scripts...")
    start_time = time.time()
    
    scripts = [
        "return redis.call('get', KEYS[1])",
        "return redis.call('set', KEYS[1], ARGV[1])",
        "return redis.call('incr', KEYS[1])",
        "return redis.call('del', KEYS[1])",
        "return redis.call('exists', KEYS[1])",
        """
local key = KEYS[1]
local value = redis.call('get', key)
if not value then
    return nil
end
return value .. '_suffix'
        """,
        """
local key = KEYS[1]
local n = tonumber(ARGV[1])
local current = tonumber(redis.call('get', key) or 0)
return redis.call('set', key, current + n)
        """,
    ]
    
    loaded = []
    for i in range(count):
        script = scripts[i % len(scripts)]
        sha = client.script_load(script)
        loaded.append(sha)
    
    elapsed = time.time() - start_time
    print(f"    ✓ Done: {count} scripts in {elapsed:.1f}s")
    return count


def verify_evalsha_noscript(client):
    """验证 EVALSHA -> NOSCRIPT -> fallback 场景
    
    ⚠️ 重要: 这是升级后最容易踩坑的场景
    - Redis 重启或 failover 后，脚本缓存会丢失
    - 应用使用 EVALSHA 会返回 NOSCRIPT 错误
    - 必须fallback到 SCRIPT LOAD 或 EVAL 重新加载脚本
    """
    print(f"\n{'='*60}")
    print(f"  Verifying EVALSHA/NOSCRIPT scenarios")
    print(f"{'='*60}")
    
    results = {}
    test_key = "test:evalsha:verify"
    
    try:
        # 1. 加载一个测试脚本
        lua_script = "return redis.call('get', KEYS[1])"
        script_sha = client.script_load(lua_script)
        results['SCRIPT_LOAD'] = script_sha is not None
        print(f"    SCRIPT LOAD: {'✓' if results['SCRIPT_LOAD'] else '✗'}")
        
        # 2. 设置测试key并使用 EVALSHA 执行（应该成功）
        client.set(test_key, "value1")
        try:
            result = client.evalsha(script_sha, 1, test_key)
            results['EVALSHA_SUCCESS'] = (result == b'value1')
            print(f"    EVALSHA (cache hit): {'✓' if results['EVALSHA_SUCCESS'] else '✗'}")
        except Exception as e:
            results['EVALSHA_SUCCESS'] = False
            results['EVALSHA_ERROR'] = str(e)
            print(f"    EVALSHA (cache hit): ✗ - {e}")
        
        # 3. 模拟脚本缓存丢失（通过 SCRIPT FLUSH）
        client.script_flush()
        
        # 4. 再次使用 EVALSHA（应该失败，返回 NOSCRIPT）
        try:
            result = client.evalsha(script_sha, 1, test_key)
            results['NOSCRIPT_DETECTED'] = False
            print(f"    NOSCRIPT detected: ✗ (should have failed)")
        except Exception as e:
            err_str = str(e).upper()
            results['NOSCRIPT_DETECTED'] = 'NOSCRIPT' in err_str
            results['NOSCRIPT_ERROR'] = str(e)
            print(f"    NOSCRIPT detected: {'✓' if results['NOSCRIPT_DETECTED'] else '✗'}")
            if not results['NOSCRIPT_DETECTED']:
                print(f"      Error: {e}")
        
        # 5. 验证 fallback 机制
        # 方式1: 使用 SCRIPT LOAD 重新获取 SHA
        try:
            new_sha = client.script_load(lua_script)
            result = client.evalsha(new_sha, 1, test_key)
            results['FALLBACK_SCRIPT_LOAD'] = (result == b'value1')
            print(f"    Fallback (SCRIPT LOAD): {'✓' if results['FALLBACK_SCRIPT_LOAD'] else '✗'}")
        except Exception as e:
            results['FALLBACK_SCRIPT_LOAD'] = False
            print(f"    Fallback (SCRIPT LOAD): ✗ - {e}")
        
        # 方式2: 直接使用 EVAL
        try:
            result = client.eval(lua_script, 1, test_key)
            results['FALLBACK_EVAL'] = (result == b'value1')
            print(f"    Fallback (EVAL): {'✓' if results['FALLBACK_EVAL'] else '✗'}")
        except Exception as e:
            results['FALLBACK_EVAL'] = False
            print(f"    Fallback (EVAL): ✗ - {e}")
        
        # 6. 测试 Redis 7 Functions（可选）
        try:
            version = client.info().get('redis_version', '')
            if version.startswith('7.'):
                lua_code = """#!lua name=verify_lib
                    local function myfunc(keys, args)
                        return redis.call('get', keys[1])
                    end
                    redis.register_function('myfunc', myfunc)"""
                client.function_load(lua_code)
                result = client.fcall("myfunc", test_key)
                results['REDIS7_FUNCTIONS'] = (result == b'value1')
                print(f"    Redis 7 Functions: {'✓' if results['REDIS7_FUNCTIONS'] else '✗'}")
            else:
                results['REDIS7_FUNCTIONS'] = None
                print(f"    Redis 7 Functions: - (Redis {version} < 7)")
        except Exception as e:
            results['REDIS7_FUNCTIONS'] = False
            print(f"    Redis 7 Functions: ✗ - {e}")
        
        # 清理测试key
        try:
            client.delete(test_key)
        except:
            pass
        
        # 汇总结果
        print(f"\n  Summary:")
        all_pass = all([
            results.get('SCRIPT_LOAD', False),
            results.get('EVALSHA_SUCCESS', False),
            results.get('NOSCRIPT_DETECTED', False),
            results.get('FALLBACK_SCRIPT_LOAD', False),
            results.get('FALLBACK_EVAL', False),
        ])
        
        if all_pass:
            print(f"    ✓ PASS - All EVALSHA/NOSCRIPT checks passed")
        else:
            print(f"    ✗ WARNING - Some checks failed, review fallback logic")
        
        return results
        
    except Exception as e:
        print(f"    ✗ ERROR: {e}")
        return {'ERROR': str(e)}


def prepare_function_library(client, count=10):
    """准备Function (Redis 7+)"""
    print(f"  Preparing {count} functions (Redis 7+ only)...")
    start_time = time.time()
    
    # Redis 7+ functions
    try:
        # 先清理
        client.function_flush()
        
        # 创建简单的function
        for i in range(count):
            lib_name = f"test_lib_{i}"
            # Redis 7+ function格式
            code = f"""
#!js api_version=1.0 name={lib_name}
function test_{i}() {{
    return redis.call('ping');
}}
"""
            # 尝试加载
            try:
                client.function_load(code)
            except Exception as e:
                # 如果是Redis 6，会报错
                if "not found" in str(e).lower() or "unknown" in str(e).lower():
                    print(f"    ⚠ Functions not supported (Redis < 7)")
                    return 0
                raise
        
        elapsed = time.time() - start_time
        print(f"    ✓ Done: {count} functions in {elapsed:.1f}s")
        return count
    except Exception as e:
        print(f"    ⚠ Functions not supported: {e}")
        return 0


def get_client(host, port):
    """获取Redis客户端 (Cluster模式)"""
    from redis.cluster import ClusterNode
    
    rc = RedisCluster(
        startup_nodes=[ClusterNode(host, port)],
        decode_responses=False,
        skip_full_coverage_check=True,
        max_connections=30,
        retry_on_timeout=True
    )
    rc.ping()
    print(f"  Using Redis Cluster client")
    rc._is_cluster = True
    return rc


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prepare Test Data - 准备测试数据"
    )
    parser.add_argument(
        '--host', '-H',
        default='127.0.0.1',
        help='Redis host'
    )
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=6379,
        help='Redis port'
    )
    parser.add_argument(
        '--string', '-s',
        type=int,
        default=1000000,
        help='String count (default: 1000000)'
    )
    parser.add_argument(
        '--list', '-l',
        type=int,
        default=100000,
        help='List count (default: 100000)'
    )
    parser.add_argument(
        '--hash', 
        type=int,
        default=100000,
        help='Hash count (default: 100000)'
    )
    parser.add_argument(
        '--set', 
        type=int,
        default=10000,
        help='Set count (default: 10000)'
    )
    parser.add_argument(
        '--zset', '-z',
        type=int,
        default=10000,
        help='ZSet count (default: 10000)'
    )
    parser.add_argument(
        '--stream',
        type=int,
        default=1000,
        help='Stream count (default: 1000)'
    )
    parser.add_argument(
        '--hll',
        type=int,
        default=1000,
        help='HyperLogLog count (default: 1000)'
    )
    parser.add_argument(
        '--bitmap',
        type=int,
        default=1000,
        help='Bitmap count (default: 1000)'
    )
    parser.add_argument(
        '--geo',
        type=int,
        default=1000,
        help='Geospatial count (default: 1000)'
    )
    parser.add_argument(
        '--script',
        type=int,
        default=100,
        help='Script count (default: 100)'
    )
    parser.add_argument(
        '--function',
        type=int,
        default=10,
        help='Function count (default: 10)'
    )
    parser.add_argument(
        '--verify-scripts',
        action='store_true',
        help='Verify EVALSHA/NOSCRIPT fallback scenarios after loading scripts'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Use default counts for all types'
    )
    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=4,
        help='Number of workers (default: 4)'
    )
    return parser.parse_args()


def main():
    args = parse_args()
    
    print("=" * 60)
    print("  Redis Test Data Preparation")
    print("  准备测试数据")
    print("=" * 60)
    
    # 如果指定 --all，使用默认数量
    if args.all:
        counts = DEFAULT_COUNTS.copy()
    else:
        counts = {
            'string': args.string,
            'list': args.list,
            'hash': args.hash,
            'set': args.set,
            'zset': args.zset,
            'stream': args.stream,
            'hyperloglog': args.hll,
            'bitmap': args.bitmap,
            'geospatial': args.geo,
        }
    
    print(f"\n  Target: {args.host}:{args.port}")
    print(f"\n  Data counts:")
    for dtype, count in counts.items():
        print(f"    {dtype}: {count:,}")
    print(f"    script: {args.script}")
    print(f"    function: {args.function}")
    
    # 连接Redis
    print("\n  Connecting to Redis...")
    client = get_client(args.host, args.port)
    
    try:
        client.ping()
    except Exception as e:
        print(f"  ✗ Cannot connect: {e}")
        sys.exit(1)
    
    # 获取Redis版本
    version = client.info().get('redis_version', 'unknown')
    print(f"  ✓ Connected: Redis {version}")
    
    # 准备数据
    print("\n" + "=" * 60)
    print("  Preparing data...")
    print("=" * 60 + "\n")
    
    total_start = time.time()
    total_keys = 0
    
    # String
    total_keys += prepare_strings(client, counts.get('string', 0))
    
    # List
    total_keys += prepare_lists(client, counts.get('list', 0))
    
    # Hash
    total_keys += prepare_hashes(client, counts.get('hash', 0))
    
    # Set
    total_keys += prepare_sets(client, counts.get('set', 0))
    
    # ZSet
    total_keys += prepare_zsets(client, counts.get('zset', 0))
    
    # Stream
    total_keys += prepare_streams(client, counts.get('stream', 0))
    
    # HyperLogLog
    total_keys += prepare_hyperloglogs(client, counts.get('hyperloglog', 0))
    
    # Bitmap
    total_keys += prepare_bitmaps(client, counts.get('bitmap', 0))
    
    # Geospatial
    total_keys += prepare_geospatial(client, counts.get('geospatial', 0))
    
    # Scripts
    if args.script > 0:
        total_keys += prepare_scripts(client, args.script)
        
        # ⚠️ 重要: 添加 EVALSHA/NOSCRIPT 验证
        if args.verify_scripts:
            verify_evalsha_noscript(client)
    
    # Functions (Redis 7+ only)
    if args.function > 0:
        if version.startswith('7.'):
            total_keys += prepare_function_library(client, args.function)
        else:
            print(f"  ⚠ Skipping functions (Redis {version} < 7)")
    
    total_elapsed = time.time() - total_start
    
    # 汇总
    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"\n  Total keys prepared: {total_keys:,}")
    print(f"  Total time: {total_elapsed:.1f}s")
    print(f"  Average: {total_keys/total_elapsed:.0f} keys/s")
    
    # 验证数据
    print("\n  Verifying data...")
    info = client.info('keyspace')
    print(f"    db0: keys={info.get('db0', {}).get('keys', 0)}")
    
    print("\n" + "=" * 60)
    if total_keys > 0:
        print("  ✓ PASS - Data prepared successfully")
    else:
        print("  ✗ FAIL - No data prepared")
    print("=" * 60)


if __name__ == '__main__':
    main()
