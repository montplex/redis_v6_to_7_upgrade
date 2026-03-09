# Redis v6 -> v7 升级步骤指南

**[English Version](./guide.md)**

## 前置条件

- Python 3.8+, `redis-py` (`pip install redis`)
- 项目根目录下需要 `bin/redis-server-v6`, `bin/redis-server-v7`, `bin/redis-cli`
- 所有脚本从项目根目录运行: `/home/kerry/test_tmp/v6_to_7/upgrade/`

## 快速参考

| 步骤 | 执行脚本 | 检查脚本 | 描述 |
|------|----------|----------|------|
| 0 | `prepare_cluster_sample.py` | `check_after_do_step0.py` | 创建 v6 集群 |
| 1 | `prepare_data.py` | `check_after_do_step1.py` | 填充测试数据 |
| 2/2.5 | `pre_upgrade_check.py` + `adjust_replication_buffers.py` | `check_after_do_step2.py` | 预检查和缓冲区调整 |
| 3 | `add_v7_replica.py` | `check_after_do_step3.py` | 添加 v7 副本节点 |
| 4 | `verify_replication.py` | (同步骤3检查) | 验证复制同步 |
| 5 | `stress_test.py` | (手动检查输出) | 压力测试（可选） |
| 6 | `failover_to_v7.py` | `check_after_do_step6.py` | 升级 v7 为主节点 |
| 7 | `rollback.py` | `check_after_do_step7.py` | 回滚到 v6（如需要） |
| 10 | `failover_to_v7.py` | `check_after_do_step6.py` | 重新升级到 v7 |
| 12 | `remove_v6_nodes.py` | `check_after_do_step12.py` | 移除 v6 节点，升级完成 |

---

## 标准升级流程

### 步骤 0: 创建集群

```bash
python3 scripts/prepare_cluster_sample.py \
    --mode simulate \
    --redis-bin bin/redis-server-v6 \
    --output scripts/upgrade_config.json \
    --force

# 检查
python3 scripts/check_after_do_step0.py scripts/upgrade_config.json
```

**验证要点:**
- 9 个节点存活（3 主节点 + 6 从节点）
- 所有节点均为 v6.2.x
- `cluster_state=ok`, 16384 槽位已分配
- 配置 `new_slaves` 每个分片有 3 条记录，`host` 已设置

### 步骤 1: 准备测试数据

```bash
python3 scripts/prepare_data.py \
    --host 127.0.0.1 --port 6379 \
    --all --verify-scripts

# 检查
python3 scripts/check_after_do_step1.py scripts/upgrade_config.json
```

**验证要点:**
- 所有数据类型都有对应的 key（string/list/hash/set/zset/stream/hll/bitmap/geo）
- Lua SCRIPT LOAD + EVALSHA 工作正常

### 步骤 2 + 2.5: 预检查和调整缓冲区

```bash
# 步骤 2: 预检查
python3 scripts/pre_upgrade_check.py \
    -c scripts/upgrade_config.json \
    --skip-warnings

# 步骤 2.5: 调整 v6 主节点缓冲区
python3 scripts/adjust_replication_buffers.py \
    -c scripts/upgrade_config.json \
    --step 2.5 --auto-continue

# 检查
python3 scripts/check_after_do_step2.py scripts/upgrade_config.json
```

**验证要点:**
- `cluster_state=ok`
- 所有主节点为 v6.2.x，有 2+ 个已连接从节点
- 所有主节点 `repl-backlog-size` >= 256MB

### 步骤 3: 添加 v7 副本节点

```bash
python3 scripts/add_v7_replica.py \
    -c scripts/upgrade_config.json

# 检查
python3 scripts/check_after_do_step3.py scripts/upgrade_config.json
```

**验证要点:**
- 18 个活动节点（9 个原节点 + 9 个新 v7 节点）
- 所有 v7 副本节点为 v7.2.x，role=slave，link=up
- `cluster_state=ok`

### 步骤 4: 验证复制

```bash
python3 scripts/verify_replication.py \
    -c scripts/upgrade_config.json

# 使用同步骤 3 的检查
python3 scripts/check_after_do_step3.py scripts/upgrade_config.json
```

### 步骤 5: 压力测试（可选）

```bash
python3 scripts/stress_test.py \
    --nodes "127.0.0.1:6379,127.0.0.1:6380,127.0.0.1:6381" \
    --qps 1000 --duration 60
```

**验证要点:** 成功率 > 99%，手动检查输出。

### 步骤 6: 切换到 v7

```bash
python3 scripts/failover_to_v7.py \
    -c scripts/upgrade_config.json \
    --auto-continue

# 检查
python3 scripts/check_after_do_step6.py scripts/upgrade_config.json
```

**验证要点:**
- v7 节点为主节点（每个分片的第一个 `new_slave`）
- v6 节点为从节点
- 新的 v7 主节点 `repl-backlog-size` >= 256MB
- `cluster_state=ok`

### 观察期（1-2 小时，最多 4 小时）

```bash
# 定期运行:
python3 scripts/verify_replication.py -c scripts/upgrade_config.json
python3 scripts/check_after_do_step6.py scripts/upgrade_config.json
```

**如无问题 -> 进入步骤 12。**
**如发现问题 -> 进入步骤 7（回滚）。**

---

## 回滚流程（仅在发现问题后执行）

### 步骤 7: 回滚到 v6

```bash
python3 scripts/rollback.py \
    -c scripts/upgrade_config.json \
    --auto-continue

# 检查
python3 scripts/check_after_do_step7.py scripts/upgrade_config.json
```

**验证要点:**
- v6 节点重新成为主节点
- v7 节点降级为从节点
- `cluster_state=ok`

### 步骤 8: 验证回滚后的复制

```bash
python3 scripts/verify_replication.py \
    -c scripts/upgrade_config.json
```

### 步骤 9: 回滚后压力测试（可选）

```bash
python3 scripts/stress_test.py \
    --nodes "127.0.0.1:6379,127.0.0.1:6380,127.0.0.1:6381" \
    --qps 1000 --duration 60
```

### 步骤 10: 重新切换到 v7

```bash
python3 scripts/failover_to_v7.py \
    -c scripts/upgrade_config.json \
    --auto-continue

# 检查（同步骤 6）
python3 scripts/check_after_do_step6.py scripts/upgrade_config.json
```

### 步骤 11: 验证复制

```bash
python3 scripts/verify_replication.py \
    -c scripts/upgrade_config.json
```

**然后再次进入观察期。如正常，进入步骤 12。**

---

## 最后步骤

### 步骤 12: 移除 v6 节点

```bash
python3 scripts/remove_v6_nodes.py \
    -c scripts/upgrade_config.json \
    --auto-continue

# 检查
python3 scripts/check_after_do_step12.py scripts/upgrade_config.json
```

**验证要点:**
- 所有 v6 节点已停止
- 集群中仅剩 v7 节点（9 个节点：3 主节点 + 6 从节点）
- 所有节点为 v7.2.x
- `cluster_state=ok`, 16384 槽位已分配

---

## 一键运行（用于测试）

```bash
# 标准流程（无回滚）
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

# 完整流程（含回滚）
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

## 清理（重置所有）

```bash
for port in $(seq 6379 6387) $(seq 6479 6487); do
    bin/redis-cli -p $port SHUTDOWN NOSAVE 2>/dev/null
done
rm -rf /tmp/redis_cluster_* /tmp/redis_v7_*
```

---

**[English Version](./guide.md)**
