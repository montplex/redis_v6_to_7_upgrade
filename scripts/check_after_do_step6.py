#!/usr/bin/env python3
"""Check after Step 6/10: Verify v7 nodes are masters, v6 nodes are slaves."""

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

    print("=== Step 6/10 Check: Failover to v7 ===\n")

    for shard in shards:
        shard_idx = shard['shard_index']
        old_master_port = shard['master']['port']
        new_slaves = shard.get('new_slaves', [])

        # The first new_slave should be the new master (replica_index=1)
        if not new_slaves:
            errors.append(f"Shard {shard_idx}: no new_slaves configured")
            continue

        new_master_port = new_slaves[0]['port']
        new_master_host = new_slaves[0].get('host', '127.0.0.1')

        print(f"Shard {shard_idx}:")

        # Check new v7 master
        n = RedisNode(host=new_master_host, port=new_master_port)
        if not n.ping():
            errors.append(f"Shard {shard_idx}: v7 node :{new_master_port} is DOWN")
            print(f"  [FAIL] v7 :{new_master_port} - not responding")
            continue

        ver = get_redis_version(n)
        info = n.info('replication')
        role = info.get('role', '')
        connected = info.get('connected_slaves', 0)

        if role == 'master' and '7.' in ver:
            print(f"  [OK]   v7 :{new_master_port} - master, v{ver}, {connected} slaves")
        else:
            errors.append(f"Shard {shard_idx}: v7 :{new_master_port} role={role}, ver={ver}")
            print(f"  [FAIL] v7 :{new_master_port} - role={role}, v{ver}")

        # Check old v6 master is now slave
        old_n = RedisNode(host='127.0.0.1', port=old_master_port)
        if old_n.ping():
            old_info = old_n.info('replication')
            old_role = old_info.get('role', '')
            old_link = old_info.get('master_link_status', '')
            if old_role == 'slave':
                print(f"  [OK]   v6 :{old_master_port} - slave, link={old_link}")
            else:
                errors.append(f"Shard {shard_idx}: v6 :{old_master_port} role={old_role}, expected slave")
                print(f"  [FAIL] v6 :{old_master_port} - role={old_role}")
        else:
            print(f"  [WARN] v6 :{old_master_port} - not responding (may be removed)")

        # Check replication buffer on new master
        try:
            backlog = n.execute_command('CONFIG', 'GET', 'repl-backlog-size')
            if isinstance(backlog, list):
                val = backlog[1]
                if isinstance(val, bytes):
                    val = val.decode()
                val_mb = int(val) // (1024 * 1024)
                if val_mb >= 256:
                    print(f"  [OK]   v7 :{new_master_port} repl-backlog={val_mb}MB")
                else:
                    errors.append(f"Shard {shard_idx}: v7 master backlog={val_mb}MB, expected >= 256MB")
                    print(f"  [FAIL] v7 :{new_master_port} repl-backlog={val_mb}MB (< 256MB)")
        except Exception as e:
            print(f"  [WARN] buffer check: {e}")

    # Cluster state
    # Use first v7 master to check
    first_v7_port = shards[0]['new_slaves'][0]['port']
    first_v7_host = shards[0]['new_slaves'][0].get('host', '127.0.0.1')
    node = RedisNode(host=first_v7_host, port=first_v7_port)
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
        print("PASS - Step 6/10 v7 masters active, v6 demoted")


if __name__ == '__main__':
    main()
