#!/usr/bin/env python3
"""Check after Step 3: Verify v7 replicas added and replicating."""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import RedisNode, get_redis_version

DEFAULT_CONFIG = os.path.join(os.path.dirname(__file__), 'upgrade_config.json')


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG
    with open(config_path) as f:
        config = json.load(f)

    errors = []
    shards = config.get('shards', [])

    print("=== Step 3 Check: v7 Replicas Added ===\n")

    # Get cluster nodes from first master
    first_master = shards[0]['master']
    node = RedisNode(host=first_master['host'], port=first_master['port'])
    nodes_raw = node.execute_command('CLUSTER', 'NODES')
    if isinstance(nodes_raw, bytes):
        nodes_raw = nodes_raw.decode('utf-8')

    # Count total nodes (excluding noaddr)
    active_nodes = [l for l in nodes_raw.strip().split('\n') if 'noaddr' not in l and l.strip()]
    expected_total = sum(1 + len(s.get('slaves', [])) + len(s.get('new_slaves', [])) for s in shards)
    print(f"Active cluster nodes: {len(active_nodes)} (expected: {expected_total})")
    if len(active_nodes) < expected_total:
        # Gossip may not have propagated fully yet, warn but don't fail
        print(f"  [WARN] Gossip may still be propagating ({len(active_nodes)} < {expected_total})")

    # Check each shard's v7 replicas
    for shard in shards:
        shard_idx = shard['shard_index']
        master_port = shard['master']['port']
        new_slaves = shard.get('new_slaves', [])

        print(f"\nShard {shard_idx} (master :{master_port}):")

        for ns in new_slaves:
            port = ns['port']
            host = ns.get('host', '127.0.0.1')
            n = RedisNode(host=host, port=port)

            # Check alive
            if not n.ping():
                errors.append(f"v7 node :{port} is DOWN")
                print(f"  [FAIL] :{port} - not responding")
                continue

            # Check version is v7
            ver = get_redis_version(n)
            if '7.' not in ver:
                errors.append(f":{port} version={ver}, expected v7.x")
                print(f"  [FAIL] :{port} - version {ver}")
                continue

            # Check replication
            info = n.info('replication')
            role = info.get('role', '')
            link = info.get('master_link_status', '')

            if role == 'slave' and link == 'up':
                print(f"  [OK]   :{port} - v{ver}, role={role}, link={link}")
            elif role == 'slave':
                # link might be down momentarily, wait and retry
                time.sleep(2)
                info = n.info('replication')
                link = info.get('master_link_status', '')
                if link == 'up':
                    print(f"  [OK]   :{port} - v{ver}, role={role}, link={link} (after retry)")
                else:
                    errors.append(f":{port} role={role}, link={link}")
                    print(f"  [WARN] :{port} - v{ver}, role={role}, link={link}")
            else:
                errors.append(f":{port} role={role}, expected slave")
                print(f"  [FAIL] :{port} - v{ver}, role={role}")

    # Check cluster state still ok
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
        print("PASS - Step 3 all v7 replicas added and replicating")


if __name__ == '__main__':
    main()
