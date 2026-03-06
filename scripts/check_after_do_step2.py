#!/usr/bin/env python3
"""Check after Step 2/2.5: Verify pre-upgrade checks pass and buffers are set."""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import RedisNode, get_redis_version

DEFAULT_CONFIG = os.path.join(os.path.dirname(__file__), 'upgrade_config.json')


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG
    with open(config_path) as f:
        config = json.load(f)

    errors = []
    shards = config.get('shards', [])

    print("=== Step 2/2.5 Check: Pre-upgrade & Buffers ===\n")

    # 1. Cluster state
    first_master = shards[0]['master']
    node = RedisNode(host=first_master['host'], port=first_master['port'])
    info_raw = node.execute_command('CLUSTER', 'INFO')
    if isinstance(info_raw, bytes):
        info_raw = info_raw.decode('utf-8')

    for line in info_raw.split('\n'):
        if line.startswith('cluster_state:'):
            state = line.split(':')[1].strip()
            if state == 'ok':
                print(f"  [OK]   cluster_state={state}")
            else:
                errors.append(f"cluster_state={state}")
                print(f"  [FAIL] cluster_state={state}")

    # 2. All nodes v6
    print("\nVersion check:")
    for shard in shards:
        port = shard['master']['port']
        n = RedisNode(host='127.0.0.1', port=port)
        ver = get_redis_version(n)
        if '6.' in ver:
            print(f"  [OK]   Master :{port} = {ver}")
        else:
            errors.append(f"Master :{port} version={ver}, expected v6.x")
            print(f"  [FAIL] Master :{port} = {ver}")

    # 3. Replication links up
    print("\nReplication status:")
    for shard in shards:
        port = shard['master']['port']
        n = RedisNode(host='127.0.0.1', port=port)
        info = n.info('replication')
        role = info.get('role', '')
        connected = info.get('connected_slaves', 0)
        if role == 'master' and connected >= 2:
            print(f"  [OK]   Master :{port} role={role}, connected_slaves={connected}")
        else:
            errors.append(f"Master :{port} role={role}, connected_slaves={connected}")
            print(f"  [FAIL] Master :{port} role={role}, connected_slaves={connected}")

    # 4. Replication buffers (Step 2.5)
    print("\nReplication buffer check (Step 2.5):")
    for shard in shards:
        port = shard['master']['port']
        n = RedisNode(host='127.0.0.1', port=port)
        try:
            backlog = n.execute_command('CONFIG', 'GET', 'repl-backlog-size')
            if isinstance(backlog, list):
                val = backlog[1]
                if isinstance(val, bytes):
                    val = val.decode()
                val_mb = int(val) // (1024 * 1024)
                if val_mb >= 256:
                    print(f"  [OK]   Master :{port} repl-backlog-size={val_mb}MB")
                else:
                    errors.append(f"Master :{port} repl-backlog-size={val_mb}MB, expected >= 256MB")
                    print(f"  [FAIL] Master :{port} repl-backlog-size={val_mb}MB (< 256MB)")
        except Exception as e:
            errors.append(f"Master :{port} buffer check: {e}")
            print(f"  [FAIL] Master :{port} buffer check: {e}")

    print(f"\n{'='*40}")
    if errors:
        print(f"FAIL - {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("PASS - Step 2/2.5 checks OK, buffers configured")


if __name__ == '__main__':
    main()
