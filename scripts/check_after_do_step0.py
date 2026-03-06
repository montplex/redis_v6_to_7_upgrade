#!/usr/bin/env python3
"""Check after Step 0: Verify cluster is created correctly."""

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
    all_ports = []

    # 1. Check all nodes are alive and v6
    print("=== Step 0 Check: Cluster Created ===\n")

    for shard in shards:
        master = shard['master']
        all_ports.append(master['port'])
        for s in shard.get('slaves', []):
            all_ports.append(s['port'])

    print(f"Checking {len(all_ports)} nodes...")
    for port in all_ports:
        node = RedisNode(host='127.0.0.1', port=port)
        if not node.ping():
            errors.append(f"Node 127.0.0.1:{port} is DOWN")
            print(f"  [FAIL] 127.0.0.1:{port} - not responding")
            continue

        ver = get_redis_version(node)
        if '6.' not in ver:
            errors.append(f"Node 127.0.0.1:{port} version={ver}, expected v6.x")
        print(f"  [OK]   127.0.0.1:{port} - {ver}")

    # 2. Check cluster state
    first_master = shards[0]['master']
    node = RedisNode(host=first_master['host'], port=first_master['port'])
    info_raw = node.execute_command('CLUSTER', 'INFO')
    if isinstance(info_raw, bytes):
        info_raw = info_raw.decode('utf-8')

    cluster_state = None
    slots_assigned = None
    for line in info_raw.split('\n'):
        if line.startswith('cluster_state:'):
            cluster_state = line.split(':')[1].strip()
        if line.startswith('cluster_slots_assigned:'):
            slots_assigned = line.split(':')[1].strip()

    print(f"\nCluster state: {cluster_state}")
    if cluster_state != 'ok':
        errors.append(f"cluster_state={cluster_state}, expected ok")

    print(f"Slots assigned: {slots_assigned}")
    if slots_assigned != '16384':
        errors.append(f"slots_assigned={slots_assigned}, expected 16384")

    # 3. Check masters count
    nodes_raw = node.execute_command('CLUSTER', 'NODES')
    if isinstance(nodes_raw, bytes):
        nodes_raw = nodes_raw.decode('utf-8')

    masters = [l for l in nodes_raw.strip().split('\n') if 'master' in l.split()[2] and 'noaddr' not in l]
    slaves = [l for l in nodes_raw.strip().split('\n') if 'slave' in l.split()[2] and 'noaddr' not in l]

    print(f"Masters: {len(masters)}, Slaves: {len(slaves)}")
    if len(masters) != len(shards):
        errors.append(f"Expected {len(shards)} masters, got {len(masters)}")

    # 4. Check config has new_slaves populated
    for shard in shards:
        ns = shard.get('new_slaves', [])
        has_host = all(s.get('host') for s in ns)
        if len(ns) < 3 or not has_host:
            errors.append(f"Shard {shard['shard_index']}: new_slaves incomplete ({len(ns)} entries, hosts={'set' if has_host else 'missing'})")
        print(f"Shard {shard['shard_index']}: {len(ns)} new_slaves configured, hosts={'OK' if has_host else 'MISSING'}")

    # 5. Check config slaves match actual topology
    print("\nSlave mapping check:")
    master_id_map = {}
    for line in nodes_raw.strip().split('\n'):
        parts = line.split()
        if 'noaddr' in parts[2]:
            continue
        addr = parts[1].split('@')[0]
        port = int(addr.rsplit(':', 1)[1])
        if 'master' in parts[2]:
            master_id_map[parts[0]] = port

    for line in nodes_raw.strip().split('\n'):
        parts = line.split()
        if 'slave' not in parts[2] or 'noaddr' in parts[2]:
            continue
        addr = parts[1].split('@')[0]
        slave_port = int(addr.rsplit(':', 1)[1])
        master_id = parts[3]
        actual_master_port = master_id_map.get(master_id, '?')

        # Find in config
        found = False
        for shard in shards:
            if shard['master']['port'] == actual_master_port:
                config_slave_ports = [s['port'] for s in shard.get('slaves', [])]
                if slave_port in config_slave_ports:
                    found = True
                    break
        if not found and slave_port < 6400:  # only check v6 slaves
            errors.append(f"Slave :{slave_port} -> master :{actual_master_port} not in config")
            print(f"  [WARN] :{slave_port} -> :{actual_master_port} (not in config)")
        else:
            print(f"  [OK]   :{slave_port} -> :{actual_master_port}")

    # Result
    print(f"\n{'='*40}")
    if errors:
        print(f"FAIL - {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("PASS - Step 0 cluster is healthy")


if __name__ == '__main__':
    main()
