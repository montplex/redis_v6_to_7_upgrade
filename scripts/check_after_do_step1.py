#!/usr/bin/env python3
"""Check after Step 1: Verify test data was prepared correctly."""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from redis.cluster import RedisCluster, ClusterNode
except ImportError:
    print("Please install redis-py: pip install redis")
    sys.exit(1)

DEFAULT_CONFIG = os.path.join(os.path.dirname(__file__), 'upgrade_config.json')


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG
    with open(config_path) as f:
        config = json.load(f)

    # Connect to cluster
    shards = config.get('shards', [])
    startup_nodes = [ClusterNode(s['master']['host'], s['master']['port']) for s in shards]

    try:
        rc = RedisCluster(startup_nodes=startup_nodes, decode_responses=False)
    except Exception as e:
        print(f"FAIL - Cannot connect to cluster: {e}")
        sys.exit(1)

    errors = []
    print("=== Step 1 Check: Test Data Prepared ===\n")

    # Check each data type by sampling keys
    # Check each type by scanning for first matching key
    type_patterns = [
        ("string", "test:string:*", b"string"),
        ("list",   "test:list:*",   b"list"),
        ("hash",   "test:hash:*",   b"hash"),
        ("set",    "test:set:*",    b"set"),
        ("zset",   "test:zset:*",   b"zset"),
        ("stream", "test:stream:*", b"stream"),
        ("hll",    "test:hll:*",    b"string"),
        ("bitmap", "test:bitmap:*", b"string"),
        ("geo",    "test:geo:*",    b"zset"),
    ]

    for dtype, pattern, expected_type in type_patterns:
        sample_key = None
        for key in rc.scan_iter(match=pattern, count=10):
            sample_key = key
            break

        if not sample_key:
            errors.append(f"{dtype}: no keys matching '{pattern}' found")
            print(f"  [FAIL] {dtype}: no keys found")
            continue

        actual_type = rc.type(sample_key)
        if actual_type != expected_type:
            errors.append(f"{dtype}: type={actual_type}, expected={expected_type}")
            print(f"  [WARN] {dtype}: type={actual_type} (expected {expected_type})")
        else:
            key_name = sample_key.decode() if isinstance(sample_key, bytes) else sample_key
            print(f"  [OK]   {dtype}: key exists (e.g. {key_name}), type={actual_type.decode()}")

    # Count keys per type via scan (sample first 500 per pattern)
    print("\nKey counts (sampled):")
    type_prefixes = [
        ("string", "test:string:*"),
        ("list",   "test:list:*"),
        ("hash",   "test:hash:*"),
        ("set",    "test:set:*"),
        ("zset",   "test:zset:*"),
        ("stream", "test:stream:*"),
    ]

    total_keys = 0
    for dtype, pattern in type_prefixes:
        count = 0
        for key in rc.scan_iter(match=pattern, count=500):
            count += 1
            if count >= 500:
                break
        total_keys += count
        status = "OK" if count > 0 else "FAIL"
        print(f"  [{status:4s}] {dtype}: >= {count} keys")
        if count == 0:
            errors.append(f"{dtype}: 0 keys found")

    # Check lua scripts loaded
    print("\nLua scripts:")
    first_master = shards[0]['master']
    import redis
    r = redis.Redis(host=first_master['host'], port=first_master['port'])
    try:
        # Try a simple script
        sha = r.script_load("return 1")
        result = r.evalsha(sha, 0)
        print(f"  [OK]   SCRIPT LOAD + EVALSHA works (result={result})")
    except Exception as e:
        errors.append(f"Lua script test failed: {e}")
        print(f"  [FAIL] Lua script test: {e}")

    # Total dbsize across cluster
    print(f"\nTotal keys sampled: >= {total_keys}")

    print(f"\n{'='*40}")
    if errors:
        print(f"FAIL - {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("PASS - Step 1 test data is present")


if __name__ == '__main__':
    main()
