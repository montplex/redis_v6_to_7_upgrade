# Redis v6 -> v7 Upgrade Step-by-Step Guide

## Prerequisites

- Python 3.8+, `redis-py` (`pip install redis`)
- `bin/redis-server-v6`, `bin/redis-server-v7`, `bin/redis-cli` in project root
- All scripts run from the project root: `/home/kerry/test_tmp/v6_to_7/upgrade/`

## Quick Reference

| Step | Action Script | Check Script | Description |
|------|--------------|--------------|-------------|
| 0 | `prepare_cluster_sample.py` | `check_after_do_step0.py` | Create v6 cluster |
| 1 | `prepare_data.py` | `check_after_do_step1.py` | Fill test data |
| 2/2.5 | `pre_upgrade_check.py` + `adjust_replication_buffers.py` | `check_after_do_step2.py` | Pre-check & buffers |
| 3 | `add_v7_replica.py` | `check_after_do_step3.py` | Add v7 replicas |
| 4 | `verify_replication.py` | (same as step 3 check) | Verify replication sync |
| 5 | `stress_test.py` | (manual review output) | Stress test (optional) |
| 6 | `failover_to_v7.py` | `check_after_do_step6.py` | Promote v7 to master |
| 7 | `rollback.py` | `check_after_do_step7.py` | Rollback to v6 (if needed) |
| 10 | `failover_to_v7.py` | `check_after_do_step6.py` | Re-failover to v7 |
| 12 | `remove_v6_nodes.py` | `check_after_do_step12.py` | Remove v6, upgrade done |

---

## Normal Upgrade Flow

### Step 0: Create Cluster

```bash
python3 scripts/prepare_cluster_sample.py \
    --mode simulate \
    --redis-bin bin/redis-server-v6 \
    --output scripts/upgrade_config.json \
    --force

# Check
python3 scripts/check_after_do_step0.py scripts/upgrade_config.json
```

**What to verify:**
- 9 nodes alive (3 masters + 6 slaves)
- All nodes are v6.2.x
- `cluster_state=ok`, 16384 slots assigned
- Config `new_slaves` has 3 entries per shard with `host` set

### Step 1: Prepare Test Data

```bash
python3 scripts/prepare_data.py \
    --host 127.0.0.1 --port 6379 \
    --all --verify-scripts

# Check
python3 scripts/check_after_do_step1.py scripts/upgrade_config.json
```

**What to verify:**
- All data types have keys (string/list/hash/set/zset/stream/hll/bitmap/geo)
- Lua SCRIPT LOAD + EVALSHA works

### Step 2 + 2.5: Pre-upgrade Check & Adjust Buffers

```bash
# Step 2: pre-check
python3 scripts/pre_upgrade_check.py \
    -c scripts/upgrade_config.json \
    --skip-warnings

# Step 2.5: adjust buffers on v6 masters
python3 scripts/adjust_replication_buffers.py \
    -c scripts/upgrade_config.json \
    --step 2.5 --auto-continue

# Check
python3 scripts/check_after_do_step2.py scripts/upgrade_config.json
```

**What to verify:**
- `cluster_state=ok`
- All masters are v6.2.x with 2+ connected slaves
- `repl-backlog-size` >= 256MB on all masters

### Step 3: Add v7 Replicas

```bash
python3 scripts/add_v7_replica.py \
    -c scripts/upgrade_config.json

# Check
python3 scripts/check_after_do_step3.py scripts/upgrade_config.json
```

**What to verify:**
- 18 active nodes (9 original + 9 new v7)
- All v7 replicas are v7.2.x, role=slave, link=up
- `cluster_state=ok`

### Step 4: Verify Replication

```bash
python3 scripts/verify_replication.py \
    -c scripts/upgrade_config.json

# Uses same check as Step 3
python3 scripts/check_after_do_step3.py scripts/upgrade_config.json
```

### Step 5: Stress Test (Optional)

```bash
python3 scripts/stress_test.py \
    --nodes "127.0.0.1:6379,127.0.0.1:6380,127.0.0.1:6381" \
    --qps 1000 --duration 60
```

**What to verify:** Success rate > 99%, review output manually.

### Step 6: Failover to v7

```bash
python3 scripts/failover_to_v7.py \
    -c scripts/upgrade_config.json \
    --auto-continue

# Check
python3 scripts/check_after_do_step6.py scripts/upgrade_config.json
```

**What to verify:**
- v7 nodes are masters (first `new_slave` per shard)
- v6 nodes are slaves
- `repl-backlog-size` >= 256MB on new v7 masters
- `cluster_state=ok`

### Observation Period (1-2 hours, max 4 hours)

```bash
# Periodically run:
python3 scripts/verify_replication.py -c scripts/upgrade_config.json
python3 scripts/check_after_do_step6.py scripts/upgrade_config.json
```

**If no issues -> go to Step 12.**
**If issues found -> go to Step 7 (Rollback).**

---

## Rollback Flow (only if issues found)

### Step 7: Rollback to v6

```bash
python3 scripts/rollback.py \
    -c scripts/upgrade_config.json \
    --auto-continue

# Check
python3 scripts/check_after_do_step7.py scripts/upgrade_config.json
```

**What to verify:**
- v6 nodes are masters again
- v7 nodes are demoted to slaves
- `cluster_state=ok`

### Step 8: Verify Rollback Replication

```bash
python3 scripts/verify_replication.py \
    -c scripts/upgrade_config.json
```

### Step 9: Stress Test After Rollback (Optional)

```bash
python3 scripts/stress_test.py \
    --nodes "127.0.0.1:6379,127.0.0.1:6380,127.0.0.1:6381" \
    --qps 1000 --duration 60
```

### Step 10: Re-failover to v7

```bash
python3 scripts/failover_to_v7.py \
    -c scripts/upgrade_config.json \
    --auto-continue

# Check (same as Step 6)
python3 scripts/check_after_do_step6.py scripts/upgrade_config.json
```

### Step 11: Verify Replication

```bash
python3 scripts/verify_replication.py \
    -c scripts/upgrade_config.json
```

**Then enter observation period again. If OK, proceed to Step 12.**

---

## Final Step

### Step 12: Remove v6 Nodes

```bash
python3 scripts/remove_v6_nodes.py \
    -c scripts/upgrade_config.json \
    --auto-continue

# Check
python3 scripts/check_after_do_step12.py scripts/upgrade_config.json
```

**What to verify:**
- All v6 nodes are down
- Only v7 nodes in cluster (9 nodes: 3 masters + 6 slaves)
- All nodes are v7.2.x
- `cluster_state=ok`, 16384 slots assigned

---

## One-liner Full Run (for testing)

```bash
# Normal flow (no rollback)
python3 scripts/prepare_cluster_sample.py --mode simulate --redis-bin bin/redis-server-v6 --output scripts/upgrade_config.json --force && \
python3 scripts/check_after_do_step0.py scripts/upgrade_config.json && \
python3 scripts/prepare_data.py --host 127.0.0.1 --port 6379 --string 1000 --list 100 --hash 100 --set 100 --zset 100 --stream 10 --hll 10 --bitmap 10 --geo 10 --script 5 && \
python3 scripts/check_after_do_step1.py scripts/upgrade_config.json && \
python3 scripts/adjust_replication_buffers.py -c scripts/upgrade_config.json --step 2.5 --auto-continue && \
python3 scripts/check_after_do_step2.py scripts/upgrade_config.json && \
python3 scripts/add_v7_replica.py -c scripts/upgrade_config.json && \
python3 scripts/check_after_do_step3.py scripts/upgrade_config.json && \
python3 scripts/failover_to_v7.py -c scripts/upgrade_config.json --auto-continue && \
python3 scripts/check_after_do_step6.py scripts/upgrade_config.json && \
python3 scripts/remove_v6_nodes.py -c scripts/upgrade_config.json --auto-continue && \
python3 scripts/check_after_do_step12.py scripts/upgrade_config.json

# Full flow with rollback cycle
python3 scripts/prepare_cluster_sample.py --mode simulate --redis-bin bin/redis-server-v6 --output scripts/upgrade_config.json --force && \
python3 scripts/check_after_do_step0.py && \
python3 scripts/prepare_data.py --host 127.0.0.1 --port 6379 --string 1000 --list 100 --hash 100 --set 100 --zset 100 --stream 10 --hll 10 --bitmap 10 --geo 10 --script 5 && \
python3 scripts/check_after_do_step1.py && \
python3 scripts/adjust_replication_buffers.py -c scripts/upgrade_config.json --step 2.5 --auto-continue && \
python3 scripts/check_after_do_step2.py && \
python3 scripts/add_v7_replica.py -c scripts/upgrade_config.json && \
python3 scripts/check_after_do_step3.py && \
python3 scripts/failover_to_v7.py -c scripts/upgrade_config.json --auto-continue && \
python3 scripts/check_after_do_step6.py && \
python3 scripts/rollback.py -c scripts/upgrade_config.json --auto-continue && \
python3 scripts/check_after_do_step7.py && \
python3 scripts/failover_to_v7.py -c scripts/upgrade_config.json --auto-continue && \
python3 scripts/check_after_do_step6.py && \
python3 scripts/remove_v6_nodes.py -c scripts/upgrade_config.json --auto-continue && \
python3 scripts/check_after_do_step12.py
```

## Cleanup (reset everything)

```bash
for port in $(seq 6379 6387) $(seq 6479 6487); do
    bin/redis-cli -p $port SHUTDOWN NOSAVE 2>/dev/null
done
rm -rf /tmp/redis_cluster_* /tmp/redis_v7_*
```
