#!/usr/bin/env python3
"""Check after Step 7: Verify rollback - v6 nodes are masters again."""

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

    print("=== Step 7 Check: Rollback to v6 ===\n")

    for shard in shards:
        shard_idx = shard['shard_index']
        master_port = shard['master']['port']
        master_host = shard['master'].get('host', '127.0.0.1')

        print(f"Shard {shard_idx}:")

        n = RedisNode(host=master_host, port=master_port)
        if not n.ping():
            errors.append(f"Shard {shard_idx}: v6 :{master_port} is DOWN")
            print(f"  [FAIL] v6 :{master_port} - not responding")
            continue

        ver = get_redis_version(n)
        info = n.info('replication')
        role = info.get('role', '')
        connected = info.get('connected_slaves', 0)

        if role == 'master' and '6.' in ver:
            print(f"  [OK]   v6 :{master_port} - master, v{ver}, {connected} slaves")
        else:
            errors.append(f"Shard {shard_idx}: v6 :{master_port} role={role}, ver={ver}")
            print(f"  [FAIL] v6 :{master_port} - role={role}, v{ver}")

        # Check v7 nodes are now slaves
        for ns in shard.get('new_slaves', []):
            port = ns['port']
            host = ns.get('host', '127.0.0.1')
            v7n = RedisNode(host=host, port=port)
            if v7n.ping():
                v7info = v7n.info('replication')
                v7role = v7info.get('role', '')
                if v7role == 'slave':
                    print(f"  [OK]   v7 :{port} - slave (demoted)")
                else:
                    errors.append(f"Shard {shard_idx}: v7 :{port} role={v7role}, expected slave")
                    print(f"  [FAIL] v7 :{port} - role={v7role}")

    # Cluster state
    first_master = shards[0]['master']
    node = RedisNode(host=first_master['host'], port=first_master['port'])
    info_raw = node.execute_command('CLUSTER', 'INFO')
    if isinstance(info_raw, bytes):
        info_raw = info_raw.decode('utf-8')
    for line in info_raw.split('\n'):
        if line.startswith('cluster_state:'):
            state = line.split(':')[1].strip()
            print(f"\nCluster state: {state}")
            if state != 'ok':
                errors.append(f"cluster_state={state}")

    print(f"\n{'='*40}")
    if errors:
        print(f"FAIL - {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("PASS - Step 7 rollback OK, v6 masters restored")


if __name__ == '__main__':
    main()
