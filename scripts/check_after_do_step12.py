#!/usr/bin/env python3
"""Check after Step 12: Verify all v6 nodes removed, only v7 remains."""

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

    print("=== Step 12 Check: v6 Nodes Removed ===\n")

    # 1. Check v6 nodes are all down
    print("v6 nodes (should be down):")
    for shard in shards:
        for port_source in [shard['master']] + shard.get('slaves', []):
            port = port_source['port']
            host = port_source.get('host', '127.0.0.1')
            n = RedisNode(host=host, port=port)
            if n.ping():
                errors.append(f"v6 node :{port} is still running")
                print(f"  [FAIL] :{port} - still alive!")
            else:
                print(f"  [OK]   :{port} - down")

    # 2. Find a live v7 node to query cluster
    v7_node = None
    for shard in shards:
        for ns in shard.get('new_slaves', []):
            port = ns['port']
            host = ns.get('host', '127.0.0.1')
            n = RedisNode(host=host, port=port)
            if n.ping():
                v7_node = n
                break
        if v7_node:
            break

    if not v7_node:
        print("\n[FAIL] No v7 node responding")
        sys.exit(1)

    # 3. Check cluster nodes - only v7
    print("\nCluster nodes (should be v7 only):")
    nodes_raw = v7_node.execute_command('CLUSTER', 'NODES')
    if isinstance(nodes_raw, bytes):
        nodes_raw = nodes_raw.decode('utf-8')

    active_nodes = []
    masters = 0
    slaves = 0
    for line in nodes_raw.strip().split('\n'):
        if not line.strip() or 'noaddr' in line:
            continue
        parts = line.split()
        addr = parts[1].split('@')[0]
        host, port_str = addr.rsplit(':', 1)
        port = int(port_str)
        flags = parts[2]

        # Skip nodes with fail flag (removed nodes not yet cleaned by gossip)
        if 'fail' in flags:
            print(f"  [SKIP] :{port} - {flags} (gossip cleanup pending)")
            continue

        n = RedisNode(host=host, port=port)
        ver = get_redis_version(n) if n.ping() else 'unknown'

        if 'master' in flags:
            masters += 1
        elif 'slave' in flags:
            slaves += 1

        active_nodes.append(port)

        if '7.' in ver:
            print(f"  [OK]   :{port} - {flags.split(',')[-1]}, v{ver}")
        elif ver == 'unknown':
            print(f"  [WARN] :{port} - {flags}, version unknown")
        else:
            errors.append(f":{port} is v{ver}, expected v7.x")
            print(f"  [FAIL] :{port} - {flags}, v{ver} (should be v7)")

    expected_masters = len(shards)
    expected_per_shard = len(shards[0].get('new_slaves', [])) if shards else 3
    expected_slaves = expected_masters * (expected_per_shard - 1)
    expected_total = expected_masters + expected_slaves

    print(f"\nTopology: {masters} masters, {slaves} slaves, {len(active_nodes)} total")
    print(f"Expected: {expected_masters} masters, {expected_slaves} slaves, {expected_total} total")

    if masters != expected_masters:
        errors.append(f"Masters: {masters}, expected {expected_masters}")
    if len(active_nodes) != expected_total:
        errors.append(f"Total nodes: {len(active_nodes)}, expected {expected_total}")

    # 4. Cluster state
    info_raw = v7_node.execute_command('CLUSTER', 'INFO')
    if isinstance(info_raw, bytes):
        info_raw = info_raw.decode('utf-8')

    for line in info_raw.split('\n'):
        if line.startswith('cluster_state:'):
            state = line.split(':')[1].strip()
            print(f"\nCluster state: {state}")
            if state != 'ok':
                errors.append(f"cluster_state={state}")
        if line.startswith('cluster_slots_assigned:'):
            slots = line.split(':')[1].strip()
            print(f"Slots assigned: {slots}")
            if slots != '16384':
                errors.append(f"slots_assigned={slots}")

    print(f"\n{'='*40}")
    if errors:
        print(f"FAIL - {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("PASS - Step 12 upgrade complete, v7-only cluster")


if __name__ == '__main__':
    main()
