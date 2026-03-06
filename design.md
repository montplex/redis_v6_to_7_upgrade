# Redis v6.2.x → v7.2.x 升级方案设计

## 1. 概述

本文档描述将Redis Cluster从6.2.x版本升级到7.2.x LTS的方案，采用主从Failover方式。

### 1.1 当前架构

| 项目 | 描述 |
|------|------|
| 部署模式 | Redis Cluster |
| Shard数量 | 3 |
| 每个Shard | 1主节点 + 2从节点（fellow replicas） |
| 总节点数 | 3主6从 = 9节点 |
| Region分布 | Region A: 3主 + 3从 / Region B: 3从（跨region） |
| Proxy | 自研Proxy，同region就近感知 |
| 高可用 | Proxy实现（无Sentinel） |
| 当前版本 | Redis 6.2.x |
| 目标版本 | Redis 7.2.x LTS |

### 1.2 升级方式

采用主从Failover方式升级，核心思想：
- 不需要双写/灰度读
- 通过新增7.2从库 → 替换旧从库 → 计划性切主 → 替换旧主的流程
- 逐shard进行，每个shard独立执行

---

## 2. 升级前检查清单

$(pwd)/bin目录下准备redis-server / redis-cli / engula-server文件。

### 2.1 环境检查

| 检查项 | 说明 |
|--------|------|
| 版本确认 | 确认当前所有节点均为6.2.x版本 |
| 集群状态 | `redis-cli cluster info` 确认集群健康 |
| 复制状态 | `INFO replication` 确认主从复制正常 |
| 延迟检查 | 确认跨region复制延迟 < 100ms |
| 内存使用 | 确认内存使用率 < 70% |
| 连接数 | 记录当前连接数基线 |
| 持久化 | 确认RDB/AOF配置正常 |

### 2.2 配置收集

```python
# 需收集的配置信息
configs = {
    "maxmemory": "配置值",
    "maxmemory-policy": "淘汰策略",
    "appendonly": "AOF开关",
    "bind": "绑定地址",
    "port": "端口",
    "requirepass": "密码",
    "masterauth": "主节点密码"
}
```

### 2.3 备份

- 在升级前执行`BGSAVE`或`bgsave`生成RDB快照
- 记录当前cluster拓扑信息

---

## 3. 升级流程（蓝绿升级方式）

### 3.1 升级策略

采用**蓝绿升级**方式，更保守安全：
- 每个Shard新增3个v7.2从节点（完整复制原拓扑）
- Failover到v7节点作为新主
- **保留v6节点作为从节点**，观察期内保持双版本共存
- 观察期过后（建议**1-2小时，最长不超过4小时**）再移除v6节点
- **重要提醒**：不建议将 mixed-version 状态挂 24-72 小时，时间越长 v6 触发 full sync 的概率越高（详见 6.2.1 节）
- 如有问题可在满足条件时回滚到v6节点

### 3.2 升级流程

```
正常升级流程:

Step 0: 准备集群 (3 shards, 1主2从)
    ↓
Step 1: 准备测试数据
    ↓
Step 2: 升级前检查
    ↓
Step 3: 添加v7从节点 (每shard 3个)
    ↓
Step 4: 验证复制状态
    ↓
Step 5: 压力测试
    ↓
Step 6: Failover到v7
    ↓
观察期 (1-2小时，最长不超过4小时)
    ↓
    ├── 无问题 ──────────→ Step 12: 移除v6节点 → 完成
    │
    └── 有问题 ─────────→ 回滚流程:
                              ↓
                         Step 7: 回滚到v6
                              ↓
                         Step 8: 验证回滚后复制
                              ↓
                         Step 9: 压力测试
                              ↓
                         Step 10: 重新Failover到v7
                              ↓
                         Step 11: 验证复制
                              ↓
                         回到观察期
```

### 3.3 Step详细说明

#### Step 0: 准备集群

启动Redis Cluster (3 shards, 1 master + 2 replicas per shard)

```
Shard 1: Master 7000 + Replicas 7007, 7008
Shard 2: Master 7001 + Replicas 7003, 7005
Shard 3: Master 7002 + Replicas 7004, 7006
```

#### Step 1: 准备测试数据

在升级前准备测试数据，覆盖所有Redis数据结构：
- String: 1M keys
- List/Hash: 100k keys
- Set/ZSet: 10k keys
- Stream/HLL/Bitmap/Geo: 1k keys
- Lua Scripts: 100

#### Step 2: 升级前检查

- 检查集群健康状态
- 检查所有节点版本
- 检查复制状态
- 检查内存和配置
- 检查命令兼容性
- **检查v6/v7默认配置差异**（详见 3.3.1 节）

#### 3.3.1 v6/v7 默认配置差异（关键参数）

> ⚠️ **重要**：以下表格中的默认值可能因具体版本和打包方式而有差异。**最稳妥的写法是以实际部署包里的 redis.conf diff 为准**。

**推荐做法**：
1. 对比 v6 和 v7 部署包的 redis.conf 文件：`diff redis6.conf redis7.conf`
2. 记录 v6 当前配置值
3. v7 节点启动时显式设置关键参数与 v6 一致（或根据业务需求调整）

**常见需关注的配置项（以官方示例为例）**：

| 参数 | 说明 | 升级建议 |
|------|------|----------|
| cluster-require-full-coverage | 控制是否要求所有 slot 可用才允许读 | 确认业务可接受 |
| cluster-allow-reads-when-down | 控制集群降级时是否允许读 | 确认业务可接受 |
| lazyfree-lazy-* 系列 | 异步删除/淘汰相关参数 | 需确认内存策略 |
| active-expire-effort | 主动过期清理努力程度 | 观察对 CPU 的影响 |
| replica-ignore-maxmemory | 从节点是否忽略 maxmemory | 可能导致从节点内存超限 |

**特别注意**：
- 官方 redis.conf 示例中，`lazyfree-lazy-eviction`、`lazyfree-lazy-expire`、`lazyfree-lazy-server-del` 在 v6.2 和 v7.2 中均为 `no`
- `replica-ignore-maxmemory` 在官方示例中为 `yes`
- `active-expire-effort` 在官方示例中为 `1`

#### Step 2.5: 调整复制缓冲区（关键）

> ⚠️ **在添加 v7 从节点之前，必须先调整 v6 master 的复制缓冲区**。
> 
> 原因：在 v6 master → v7 replica 的接入过程中，增大 backlog / output buffer 可以让全量同步过程更稳定。

```bash
# 在当前 v6 masters 上执行（7000/7001/7002）
for port in 7000 7001 7002; do
    redis-cli -p $port CONFIG SET repl-backlog-size 256mb
    redis-cli -p $port CONFIG SET client-output-buffer-limit "replica 512mb 64mb 60"
    redis-cli -p $port CONFIG REWRITE
done
```

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| repl-backlog-size | ≥256MB | 复制积压缓冲区，建议256MB以上 |
| client-output-buffer-limit (replica) | 512MB 64MB 60 | 从节点输出缓冲区硬/软限制 |

> ⚠️ **CONFIG REWRITE 说明**：默认必须紧跟 CONFIG REWRITE；若部署方式是 immutable image / ConfigMap / 由配置管理系统统一下发，且 Redis 并非从可写 redis.conf 启动，则必须通过配置管理系统持久化，不能只依赖 CONFIG SET。

完成配置差异比较后，每个Shard添加3个v7.2从节点（完整复制原拓扑）：

```
Shard 1: Master 7000 + Replicas 7007, 7008 (v6) + 7100, 7101, 7102 (v7)
Shard 2: Master 7001 + Replicas 7003, 7005 (v6) + 7103, 7104, 7105 (v7)
Shard 3: Master 7002 + Replicas 7004, 7006 (v6) + 7106, 7107, 7108 (v7)
```

命令：
```bash
# 为每个Shard启动3个v7节点并加入集群
# Shard 1
redis-cli -p 7100 CLUSTER MEET 127.0.0.1 7000
redis-cli -p 7101 CLUSTER MEET 127.0.0.1 7000
redis-cli -p 7102 CLUSTER MEET 127.0.0.1 7000

# 等待gossip协议传播，验证新节点已被集群感知
# 等待直到 CLUSTER NODES 输出中能看到新节点（通常5-10秒）
for port in 7100 7101 7102; do
    echo "Waiting for node $port to join cluster..."
    for i in {1..30}; do
        if redis-cli -p $port CLUSTER NODES | grep -q "7000"; then
            echo "Node $port can see master 7000"
            break
        fi
        sleep 1
    done
done

# 确认集群节点数量正确（9原节点 + 3新节点 = 12）
redis-cli -p 7000 CLUSTER NODES | wc -l  # 应为12

# 获取主节点ID（需在v7节点上执行，因gossip传播可能有延迟）
MASTER_ID=$(redis-cli -p 7100 CLUSTER NODES | grep "7000" | awk '{print $1}')

# 设置为从节点
redis-cli -p 7100 CLUSTER REPLICATE $MASTER_ID
redis-cli -p 7101 CLUSTER REPLICATE $MASTER_ID
redis-cli -p 7102 CLUSTER REPLICATE $MASTER_ID

# 同样方式处理 Shard 2 和 Shard 3
```

##### Step 3 回滚方案（添加v7从节点失败时）

如果在添加v7从节点过程中或之后出现问题（如内存压力过大、全量同步超时等），按以下步骤回滚：

**触发条件：**
- 内存使用率 > 85% 且持续上升
- 全量同步超过预期时间（> 30分钟）未完成
- v7从节点持续报错无法正常复制
- 集群负载异常增高

**回滚步骤（推荐方式）**：

1. **推荐：使用 redis-cli --cluster del-node 移除节点**
   ```bash
   # 官方推荐方式，参考 "Remove a node" 章节
   # 关闭v7节点
   redis-cli -p 7100 SHUTDOWN NOSAVE
   
   # 从集群中移除该节点（任意集群节点上执行）
   redis-cli --cluster del-node 127.0.0.1:7000 <v7_node_id>
   
   # 对每个v7节点重复上述操作
   ```

2. **备选：使用 CLUSTER FORGET（仅当 del-node 不可用时）**
   
   > 📖 **官方文档依据**：CLUSTER FORGET 官方文档指出：
   > - "Starting with Redis 7.2.0, the ban-list is included in cluster gossip ping/pong messages. This means that `CLUSTER FORGET` doesn't need to be sent to all nodes in a cluster."
   > - 7.2.0 之前版本需要向所有节点发送
   > - 参考: https://redis.io/docs/latest/commands/cluster-forget/
   
   > ⚠️ **重要**：在 mixed-version (6.2/7.2) 阶段，**必须对所有 remaining nodes 执行**，不要假设单点传播。

   ```bash
   # 对每个v7节点执行：
   # 1. 关闭v7节点
   redis-cli -p 7100 SHUTDOWN NOSAVE
   
   # 2. 在所有剩余节点上执行 FORGET（mixed-version 阶段必须这样做）
   for port in 7000 7001 7002 7003 7004 7005 7006 7007 7008; do
       redis-cli -p $port CLUSTER FORGET <v7_node_id>
   done
   ```

3. **验证集群状态**
   ```bash
   # 确认节点数量恢复到9个
   redis-cli -p 7000 CLUSTER NODES | wc -l
   
   # 确认集群状态正常
   redis-cli -p 7000 CLUSTER INFO
   ```

4. **验证复制状态**
   ```bash
   # 确认v6主从复制正常
   redis-cli -p 7000 INFO replication
   redis-cli -p 7007 INFO replication
   ```

**注意事项：**
- 回滚过程中v6节点仍然正常工作，服务不中断
- 如果问题出现在第一个v7节点添加时，建议立即停止添加操作并回滚
- 回滚后分析原因，确认问题解决后再重新尝试添加v7节点
- **强烈建议使用 `redis-cli --cluster del-node`**，这是官方推荐方式

#### Step 4: 验证复制状态

验证所有v7从节点与主节点的复制状态，确保数据追平。

#### Step 5: 压力测试 (可选)

运行压力测试，模拟业务负载，验证系统在升级过程中的稳定性。

#### Step 6: Failover到v7

**⚠️ 硬门禁：候选 v7 副本必须被多数 masters 识别为 replica**

在使用 CLUSTER FAILOVER 之前，必须满足以下条件：

> 📖 **官方文档依据**：CLUSTER FAILOVER 官方文档明确指出：
> - "An `OK` reply is no guarantee that the failover will succeed."
> - "A replica can only be promoted to a master if it is known as a replica by a majority of the masters in the cluster."
> - 参考: https://redis.io/docs/latest/commands/cluster-failover/

```bash
# 验证新v7副本已被多数 masters 识别
# 官方文档明确说明：CLUSTER FAILOVER 返回 OK 并不保证成功
# 如果这个新副本还没被多数 masters 认成 replica，manual failover 可能直接超时失败

# 方法1: 检查所有 master 节点的 CLUSTER REPLICAS 输出
for port in 7000 7001 7002; do
    echo "=== Master $port ==="
    redis-cli -p $port CLUSTER REPLICAS <v7_replica_node_id>
done

# 方法2: 在所有 masters 上检查 CLUSTER NODES 输出
for port in 7000 7001 7002; do
    echo "=== Master $port sees ==="
    redis-cli -p $port CLUSTER NODES | grep <v7_replica_node_id>
done
```

**硬门禁判定标准**：
- 候选 v7 副本必须出现在**所有 3 个 masters** 的 `CLUSTER REPLICAS` 输出中
- 或者在所有 masters 的 `CLUSTER NODES` 输出中，该副本的 `master` 字段指向正确的主节点
- 只有满足此条件后，才允许执行 `CLUSTER FAILOVER`

使用CLUSTER FAILOVER命令将v7从节点提升为主节点。

**重要: 按Shard顺序执行**
- 先执行 Shard 1 的 failover
- 验证 Shard 1 成功后，再执行 Shard 2 的 failover
- 验证 Shard 2 成功后，再执行 Shard 3 的 failover
- 每个Shard failover后需验证复制状态正常

```
Shard 1: Master 7100(v7) + Replicas 7101, 7102(v7) + Replicas 7000, 7007, 7008(v6)
Shard 2: Master 7103(v7) + Replicas 7104, 7105(v7) + Replicas 7001, 7003, 7005(v6)
Shard 3: Master 7106(v7) + Replicas 7107, 7108(v7) + Replicas 7002, 7004, 7006(v6)
```

即: 每个Shard有 1 v7 master + 2 v7 slaves + 3 v6 slaves = 6节点

#### Step 6.5: 再次调整新 v7 主节点复制缓冲区（关键）

> ⚠️ **failover 后立即在新 v7 masters 上再次执行**。
> 
> 原因：真正 mixed-version 的高风险窗口，是 Step 6 之后 v7 master → v6 replicas 还在挂着观察期的时候。Redis 复制文档明确写了：链路断开后，replica 会先尝试 partial resync；如果 backlog 不够或 replication ID 历史不匹配，就会退化成 full resync。

```bash
# Step 6.5: 在新 v7 主节点上执行（7100/7103/7106）
for port in 7100 7103 7106; do
    redis-cli -p $port CONFIG SET repl-backlog-size 256mb
    redis-cli -p $port CONFIG SET client-output-buffer-limit "replica 512mb 64mb 60"
    redis-cli -p $port CONFIG REWRITE
done
```

#### Step 7: 回滚到v6 (可选)

当Step 6后出现问题需要回滚时，将主节点切回v6：

```
观察期间发现问题:
- 原v6主节点（现为从节点）执行CLUSTER FAILOVER成为主节点
- v7主节点自动降为从节点跟随
```

**重要: 按Shard顺序执行（与Failover相反的顺序）**

命令 (Cluster模式):
```bash
# 在原v6主节点（现为从节点）上执行FAILOVER，将其重新提升为主节点
# 执行后，该节点成为主节点，原v7主节点自动降为从节点
redis-cli -p <原_v6_master_port> CLUSTER FAILOVER
```

**示例（Shard 1，统一端口映射）：**
```bash
# Step 6后：7100(v7) 是主节点，7000(v6原主节点) 是从节点
# 回滚时，在7000上执行FAILOVER，使其重新成为主节点
redis-cli -p 7000 CLUSTER FAILOVER

# 执行后：7000(v6) 成为主节点，7100(v7) 自动降为从节点
```

#### Step 8: 验证回滚后复制状态

验证回滚后v6主节点与从节点的复制状态正常。

#### Step 9: 压力测试 (回滚后)

再次运行压力测试，验证系统在回滚后的稳定性。

#### Step 10: 重新Failover到v7 (可选)

确认v7稳定后，重新执行Failover。

**重要: 按Shard顺序执行**
- 先执行 Shard 1 的 failover
- 验证 Shard 1 成功后，再执行 Shard 2 的 failover
- 验证 Shard 2 成功后，再执行 Shard 3 的 failover
- 每个Shard failover后需验证复制状态正常

```bash
# 在v7从节点上执行
redis-cli -p <v7_port> CLUSTER FAILOVER
```

#### Step 11: 验证复制状态

验证Failover后v7主节点与从节点的复制状态正常。

#### Step 12: 移除v6节点

观察期(建议**1-2小时，最长不超过4小时**)结束后，按以下**明确顺序**移除所有v6节点：

**⚠️ 重要背景**：
- Redis 7.2 的 RDB 版本是 version 11，旧版本不兼容
- 复制链路断掉后，如果 partial resync 不成立，会退化成 full resync（触发 RDB 全量复制）
- 跨 region 链路更容易掉进 backlog 不足 / 重同步窗口

**拆除顺序（必须严格遵守）**：

1. **第一步：先移除 Region B 的跨 region v6 replicas**
   ```bash
   # 跨 region 链路优先移除（更容易抖动）
   # 假设 7007, 7008 属于 Region B（跨 region）
   for port in 7007 7008; do
       NODE_ID=$(redis-cli -p 7100 CLUSTER NODES | grep ":$port " | awk '{print $1}')
       redis-cli -p $port SHUTDOWN NOSAVE || true
       redis-cli --cluster del-node 127.0.0.1:7100 $NODE_ID
       # 每移除 1 个节点就做一次 gate 检查
       redis-cli -p 7100 CLUSTER INFO | grep cluster_state
   done
   ```

2. **第二步：再移除 Region A 的同 region v6 replicas**
   ```bash
   # 同 region 的 v6 从节点
   for port in 7003 7004 7005 7006; do
       NODE_ID=$(redis-cli -p 7100 CLUSTER NODES | grep ":$port " | awk '{print $1}')
       redis-cli -p $port SHUTDOWN NOSAVE || true
       redis-cli --cluster del-node 127.0.0.1:7100 $NODE_ID
       # 每移除 1 个节点就做一次 gate 检查
       redis-cli -p 7100 CLUSTER INFO | grep cluster_state
   done
   ```

3. **第三步：最后移除原 v6 masters（现为从节点，是回滚锚点）**
   ```bash
   # 原 v6 主节点（现为从节点）是最后的回滚锚点，最后移除
   for port in 7000 7001 7002; do
       NODE_ID=$(redis-cli -p 7100 CLUSTER NODES | grep ":$port " | awk '{print $1}')
       redis-cli -p $port SHUTDOWN NOSAVE || true
       redis-cli --cluster del-node 127.0.0.1:7100 $NODE_ID
       # 每移除 1 个节点就做一次 gate 检查
       redis-cli -p 7100 CLUSTER INFO | grep cluster_state
   done
   ```

4. **验证最终集群状态**
   ```bash
   # 确认只剩 v7 节点（每个 shard 1 主 + 2 从 = 6 节点）
   redis-cli -p 7100 CLUSTER NODES | wc -l  # 应为 6
   redis-cli -p 7100 CLUSTER INFO
   ```

**硬性规定**：
- ✅ 观察期内**禁止 v6 节点执行 full sync / restart**
- ✅ 必须按"跨region replicas → 同region replicas → 原 masters"顺序移除
- ✅ **每移除 1 个节点就做一次 gate 检查**，不要批量 del-node
- ✅ 移除每个节点后验证集群状态正常

---

## 4. 验证脚本设计

### 4.1 脚本结构

```
scripts/
├── run_upgrade.py                # 升级流程编排器（顺序执行各Step脚本）
├── prepare_cluster_sample.py     # Step 0: 准备集群 / 收集拓扑生成配置
├── prepare_data.py               # Step 1: 准备测试数据
├── pre_upgrade_check.py          # Step 2: 升级前检查
├── adjust_replication_buffers.py # Step 2.5/6.5: 调整复制缓冲区
├── add_v7_replica.py             # Step 3: 添加v7从节点
├── verify_replication.py         # Step 4/8/11: 验证复制状态
├── stress_test.py                # Step 5/9: 压力测试
├── failover_to_v7.py             # Step 6/10: Failover到v7
├── rollback.py                   # Step 7: 回滚到v6
├── remove_v6_nodes.py            # Step 12: 移除v6节点
├── utils.py                      # 公共工具函数
└── upgrade_config.json           # 集群拓扑与升级配置
```

### 4.2 连接模式选择（重要）

脚本需要根据部署架构选择合适的连接方式：

| 部署模式 | 连接方式 | 脚本写法 |
|----------|----------|----------|
| **自研 Proxy 模式** | 单入口，Proxy 负责路由 | 可按单入口写，使用 `redis.Redis(host, port)` |
| **直连 Redis Cluster 模式** | 客户端直连集群 | **必须使用 RedisCluster / cluster-aware client** |

> ⚠️ **直连 Redis Cluster 模式的注意事项**：
> - 官方明确要求使用 cluster-aware client
> - redis-cli 需要加 `-c` 才能跟随重定向
> - 正式客户端应缓存 slot map，并在 failover / MOVED 后刷新拓扑
> - 如果不使用 cluster-aware client，会遇到 `MOVED` / `ASK` 错误
> - 也可明确所有 key 用 hash tag 固定到目标 shard

**示例代码**：

```python
# Proxy 模式（单入口）
r = redis.Redis(host='proxy.host', port=6379)

# 直连 Redis Cluster 模式
from redis.cluster import RedisCluster
r = RedisCluster(
    startup_nodes=[
        {'host': '127.0.0.1', 'port': 7000},
        {'host': '127.0.0.1', 'port': 7001},
        {'host': '127.0.0.1', 'port': 7002},
    ],
    decode_responses=False
)
```

**在验证脚本中使用时**：
- `prepare_data.py`、`stress_test.py`、`verify_replication_compatibility` 等示例
- 如果是直连 Cluster 模式，需要改成 RedisCluster 客户端
- 或者明确所有 key 用 hash tag（如 `{user}:123`）固定到目标 shard

### 4.3 验证项

| 验证项 | 命令 | 脚本 | 判定标准 |
|--------|------|------|----------|
| 节点存活 | `ping` | `pre_upgrade_check.py` | PONG |
| 角色正确 | `INFO replication` | `pre_upgrade_check.py`, `verify_replication.py` | role符合预期 |
| 复制状态 | `INFO replication` | `verify_replication.py` | master_link_status=up |
| 复制延迟 | `INFO replication` | `verify_replication.py` | slave_repl_offset与master一致 |
| 集群状态 | `CLUSTER INFO` | `pre_upgrade_check.py` | cluster_state=ok |
| 节点拓扑 | `CLUSTER NODES` | `pre_upgrade_check.py`, `verify_replication.py` | 节点数量正确，关系正确 |
| Slot分配 | `CLUSTER INFO` | `pre_upgrade_check.py` | cluster_slots_assigned=16384 |
| **EVALSHA/NOSCRIPT** | **`EVALSHA/SCRIPT LOAD/SCRIPT FLUSH`** | **`verify_evalsha_noscript`** | **NOSCRIPT错误能正确检测，fallback成功** |
| 数据完整性 | 抽样key验证 | `stress_test.py` | 随机抽样key对比 |

---

## 5. 回滚方案

### 5.1 回滚触发条件

| 条件 | 说明 |
|------|------|
| 复制延迟持续 > 10s | 复制链路不稳定 |
| 数据丢失 | 关键数据丢失 |
| 集群不可用 | cluster_state != ok |
| 业务异常 | 业务反馈严重错误 |
| 观察期内异常 | v7节点持续报错或延迟高 |

### 5.2 蓝绿模式下的回滚优势

蓝绿升级模式的核心优势：**保留v6节点，有条件回滚**

> ⚠️ **技术说明**：当前 runbook 的 shard 拓扑中，所有 replicas 都应直接跟随该 shard 当前 master；虽然 Redis 复制机制本身支持 replica-of-replica（从 Redis 4.0 起），但本方案不采用级联复制。

```
观察期内的回滚（无需停服务）：
  
  当前状态（v7为主，v6为从）：
  Shard 1:
    7100(v7) [主] ──> 7000(v6) [从]
          │
          ├─> 7101(v7) [从]
          │
          └─> 7102(v7) [从]

  回滚操作 (Cluster模式):
  1. 7000(v6) 提升为主: CLUSTER FAILOVER
  2. 其他节点挂到7000: CLUSTER REPLICATE <7000_node_id>
  3. v7节点可保留作为从或关闭
```

### 5.3 回滚步骤

如果切主后出现问题，按以下顺序回滚：

1. **停止问题节点**
2. **恢复旧主角色 (Cluster模式)**
   ```bash
   # 旧主升回主节点
   redis-cli -h M1 -p 6379 CLUSTER FAILOVER
   
   # 获取主节点ID
   redis-cli -h M1 -p 6379 CLUSTER NODES | grep myself
 
   ```
3. **验证集群恢复**
4. **分析问题原因**

---

## 6. 风险点与应对措施（蓝绿模式）

### 6.1 主要风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 跨region复制抖动 | 复制延迟增大，重同步 | 升级前确认网络稳定，观察期监控 |
| 切主时连接抖动 | 客户端短暂不可用 | Proxy做好连接重试，业务端做好重试 |
| 数据不一致 | 少量数据丢失 | 切主前短暂停写，减少不一致窗口 |
| 内存不足 | OOM导致重启 | 升级前确认内存充足 |
| **v7节点不稳定** | 业务受影响 | **保留v6节点，有条件回滚** |

### 6.2 Proxy / Client 兼容性验证（关键）

> ⚠️ **这是升级成功与否里最容易被忽略的一层**。
> 
> 📖 **官方文档依据**：CLUSTER SHARDS 官方文档指出：
> - "This command replaces the `CLUSTER SLOTS` command, by providing a more efficient and extensible representation of the cluster."
> - "A client should issue this command on startup in order to retrieve the map associating cluster *hash slots* with actual node information."
> - "In the event the command is sent to the wrong node, in that it received a '-MOVED' redirect, this command can then be used to update the topology of the cluster."
> - 参考: https://redis.io/docs/latest/commands/cluster-shards/

#### 自研 Proxy 专项验证项

如果使用自研 Proxy 连接 Redis Cluster，需验证以下 4 条：

| 验证项 | 说明 | 测试方法 |
|--------|------|----------|
| **CLUSTER SHARDS 解析** | 官方推荐用 CLUSTER SHARDS 取拓扑 | 调用 `CLUSTER SHARDS`，解析返回的 slot range 和 endpoint/port |
| **CLUSTER SLOTS 兼容回退** | 兼容老版本 Redis 或老客户端 | 如果 CLUSTER SHARDS 不可用，回退到 CLUSTER SLOTS |
| **MOVED/ASK 处理** | 收到重定向后刷新拓扑并重试 | 模拟 `MOVED` / `ASK` 错误，验证客户端自动重定向 |
| **endpoint/hostname/port 变化刷新** | failover 后 endpoint 可能变化 | 执行 failover 后，验证 Proxy 能感知并刷新连接 |

**测试脚本示例**：

```python
def verify_proxy_cluster_compatibility(proxy_host, proxy_port):
    """验证 Proxy 对 Redis Cluster 的兼容性"""
    import socket
    
    results = {}
    
    # 1. CLUSTER SHARDS 解析
    r = redis.Redis(host=proxy_host, port=proxy_port)
    try:
        shards = r.execute_command('CLUSTER', 'SHARDS')
        results['CLUSTER_SHARDS'] = len(shards) > 0
    except Exception as e:
        results['CLUSTER_SHARDS'] = False
        results['CLUSTER_SHARDS_ERROR'] = str(e)
    
    # 2. CLUSTER SLOTS 兼容回退
    try:
        slots = r.execute_command('CLUSTER', 'SLOTS')
        results['CLUSTER_SLOTS'] = len(slots) > 0
    except Exception as e:
        results['CLUSTER_SLOTS'] = False
    
    # 3. MOVED 处理验证（需要模拟或检查日志）
    # 通过执行跨 slot 操作触发 MOVED，检查 Proxy 是否正确处理
    
    # 4. Failover 后拓扑刷新验证
    # 在 failover 前后检查 Proxy 的连接状态
    
    return results
```

**关键提醒**：
- 客户端应在启动时拉取 slot map
- 收到 `-MOVED` 后刷新拓扑，并按返回的 endpoint/port 重连
- 建议在升级演练中模拟 failover，验证 Proxy 能否正确处理

#### 6.2.2 Proxy 拓扑感知验收标准（关键）

> ⚠️ **这是升级验收的核心指标之一**。
> 
> Redis Cluster 客户端和代理必须根据集群拓扑把请求路由到正确节点；官方对 CLUSTER SLOTS 的描述明确写了，它就是给客户端库拿 slot→node 映射用的，在收到重定向时要更新映射；7.0 起官方建议新代码改用 CLUSTER SHARDS。

**验收指标**：

| 指标 | 说明 | 达标标准 |
|------|------|----------|
| **拓扑刷新耗时** | 每个 shard failover 后，Proxy 从"收到旧拓扑"到"写请求成功打到新 master"的耗时 | ≤ 30秒（建议值） |
| **路由正确性** | failover 后所有写请求打到正确的 shard master | 100% |

**验证方法**：

```bash
# 1. 在 Proxy 层发起验证请求
redis-cli -h <proxy_host> -p <proxy_port> SET failover:check:shard1 "ok"

# 2. 验证请求是否打到新 master（7100 是 Shard 1 的新 v7 master）
redis-cli -p 7100 GET failover:check:shard1

# 3. 预期结果：
# - 如果返回 "ok"，说明请求成功打到新 master
# - 如果返回 nil，说明请求可能打到了旧节点或拓扑未刷新
```

**硬性要求**：
- ✅ 每个 shard failover 后，必须记录 Proxy 拓扑刷新的实际耗时
- ✅ 耗时指标纳入升级验收标准
- ✅ 如超过 30 秒，必须排查 Proxy 拓扑刷新机制

### 6.3 Redis v6/v7 兼容性风险（关键）

#### 6.3.1 RDB版本不兼容

| 项目 | Redis v6 | Redis v7 |
|------|----------|----------|
| RDB版本 | version 9 | version 11 |
| 兼容性 | v6无法加载v7的RDB | v7可加载v6的RDB |

**风险说明**：
- 升级完成后，v6从节点**不能重启**，重启会触发RDB全量复制
- v7主节点的RDB无法被v6从节点正确加载

**⚠️ 运行时重同步风险（关键补充）**：

上述风险不仅仅是"不要重启"的问题，**运行期间就可能发生**：

1. **触发条件**：当复制积压缓冲区溢出时（网络抖动、写入量大），v7主节点会触发全量重同步
2. **后果**：v7主节点向v6从节点发送RDB v11文件，v6从节点无法加载，导致复制中断
3. **场景**：
   - 网络抖动导致复制中断
   - 写入量大导致 repl-backlog-size 不够
   - 跨 region 复制延迟增大

**应对措施**：

1. **禁止重启v6节点**：
   - 观察期内**禁止重启v6节点**
   - 观察期后统一按顺序移除v6节点（先移除从节点，最后移除主节点）
   - 如必须重启v6节点，需先确认是否有其他v7从节点可作为备选

2. **增大复制缓冲区（强制）**：
   ```bash
   # 在v7主节点上显著增大复制积压缓冲区
   CONFIG SET repl-backlog-size 256mb
   
   # 增大从节点客户端输出缓冲区
   CONFIG SET client-output-buffer-limit replica 512MB 64MB 60
   ```
   
   | 参数 | 推荐值 | 说明 |
   |------|--------|------|
   | repl-backlog-size | ≥256MB | 复制积压缓冲区，建议256MB以上 |
   | client-output-buffer-limit (replica) | 512MB 64MB 60 | 从节点输出缓冲区硬/软限制 |

3. **持续监控v6从节点状态**：
   - 监控 `INFO replication` 中的 `master_link_status`
   - 监控 `slave_repl_offset` 与主节点的延迟
   - 告警阈值：master_link_status=down 持续 > 10s

4. **制定明确预案**：当v6从节点失去同步时，**直接移除，不要尝试重新同步**
   - 一旦检测到 v6 从节点 master_link_status=down
   - 立即执行 `CLUSTER FORGET` 移除该节点
   - 不要尝试使用 `CLUSTER REPLICATE` 重新建立复制关系
   - 因为重新同步会触发 RDB 全量复制，必然失败

### 6.4 命令行为差异风险

> **注意**: 以下关于runtest的结论仅作为参考。redis v6 unit tests external模式测试redis v7这种方式有局限性（框架限制），不能完全覆盖所有场景。实际兼容性需结合客户历史命令日志分析。

根据runtest和clients_compatibility测试结果，v6与v7存在以下命令行为差异：

#### 6.4.1 v6独有错误（v7正常）

| 命令/特性 | 问题 | 影响 |
|-----------|------|------|
| cluster节点管理 | 节点清理有时报错 | 资源清理 |
| 二进制值SET/GET | 语法受限 | 二进制操作 |

#### 6.4.2 v7独有失败（v6正常）

| 命令/特性 | 问题 | 影响 |
|-----------|------|------|
| CLUSTER SHARDS | API返回结构变化 | Jedis客户端兼容 |

#### 6.4.3 需验证的Corner Cases

以下命令在升级后可能存在行为差异，建议在验证脚本中覆盖：

| 序号 | 命令/场景 | 验证点 | 风险等级 |
|------|-----------|--------|----------|
| 1 | `SET key value GET` | v6.2+返回旧值，v6.0/v6.1返回nil | 中 |
| 2 | `BLPOP` timeout | 时间精度差异 | 低 |
| 3 | `CLUSTER SHARDS` | 返回格式变化 | 中 |
| 4 | `GEORADIUS` 系列 | 某些参数行为变化 | 低 |
| 5 | `PUBSUB` | Cluster模式行为 | 中 |
| 6 | `SCRIPT LOAD` | Lua脚本缓存格式 | 中 |
| 7 | `EVALSHA` -> `NOSCRIPT` | 脚本缓存miss后的fallback | **高** |
| 8 | `SCRIPT FLUSH` | 清空缓存后EVALSHA失败 | **高** |
| 9 | Redis 7 Functions | 持久化脚本（替代方案） | 中 |
| 10 | `BITFIELD` | 有符号/无符号处理 | 低 |
| 11 | `HASH`ziplist编码 | 转换阈值变化 | 低 |
| 12 | `LIST` quicklist | v7使用新编码 | 低 |
| 13 | `STREAM` | v5+已有特性（v7有增强） | 低 |

### 6.5 蓝绿模式的风险降低

| 风险点 | 传统方式 | 蓝绿模式 |
|--------|----------|----------|
| 升级失败 | 需要重建集群 | 切回v6节点即可 |
| 观察期发现问题 | 无法回滚 | v6保留，有条件回滚 |
| 业务反馈异常 | 可能需要紧急回滚 | 观察期有缓冲 |

### 6.6 最佳实践

| 操作 | 建议 |
|------|------|
| 切主时机 | 选择业务低峰期 |
| 停写窗口 | 控制在30秒以内 |
| 验证间隔 | 每步操作后立即验证 |
| 监控告警 | 开启复制延迟、连接数监控 |

---

## 7. 升级检查点（蓝绿模式）

| 阶段 | 检查点 | 验证命令 |
|------|--------|----------|
| Step 0 | 集群准备完成 | cluster nodes, 9 nodes |
| Step 1 | 测试数据就绪 | dbsize > 0 |
| Step 2 | 集群健康检查 | cluster state=ok |
| Step 3 | v7节点已添加 | 每个shard有3个v7从节点 |
| Step 4 | 复制追平 | repl_offset 对齐 |
| Step 5 | 压力测试通过 | 成功率 > 99% |
| Step 6 | Failover完成 | 新主role=master |
| Step 7 | 回滚(如需要) | 原v6主节点恢复为主 |
| Step 8 | 验证回滚后复制 | repl_offset 对齐 |
| Step 9 | 压力测试(回滚后) | 成功率 > 99% |
| Step 10 | 重新Failover | v7再次成为主 |
| Step 11 | 验证复制 | repl_offset 对齐 |
| Step 12 | 移除v6节点 | v6节点已关闭 |

### 7.1 观察期检查清单（1-2小时，最长不超过4小时）

> ⚠️ **观察期仅 1-2 小时（最长 4 小时），不是"每日"，应是连续监控或每 5-15 分钟巡检**

```
连续监控项 / 每 5-15 分钟巡检项：
□ 复制延迟 < 500ms（跨region可放宽）
□ 无master_link_status=down
□ 客户端连接数稳定
□ 业务读写延迟P99无明显增长
□ Redis错误日志无ERROR级别
□ 内存使用率稳定

如发现问题：
□ 评估是否需要回滚
□ 回滚操作：M1提升为主，其他节点跟随
```

### 7.2 观察期后的决策

**决策时间线**：

| 时间点 | 里程碑 | 参与方 |
|--------|--------|--------|
| failover 后 5-10 分钟 | 第一轮技术指标确认 | 运维/DBA |
| failover 后 30 分钟 | 业务方第一轮验证 | 业务方 |
| failover 后 60-120 分钟 | 联合决策是否拆除 v6 | 运维/DBA + 业务方 |

```
观察期结束后的决策树：

  ┌─────────────────────────────────────────┐
  │            观察期结束                     │
  └─────────────────┬───────────────────────┘
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
     无异常                  有异常
          │                   │
          ▼                   ▼
    移除v6节点           继续保留v6节点
    升级完成             或回滚到v6
```

---

## 8. Corner Cases 验证（重要）

> **注意**: 以下验证场景基于runtest测试结果，仅供参考。实际验证需结合客户历史命令日志分析结果针对性覆盖。

### 8.1 验证脚本需覆盖的场景

基于runtest和clients_compatibility测试结果，以下场景需在验证脚本中覆盖：

#### 8.1.1 命令兼容性验证

```python
def verify_command_compatibility(master_host, password=None):
    """验证关键命令在v7上的行为"""
    r = redis.Redis(host=master_host, password=password)
    
    results = {}
    
    # 1. SET with GET parameter (v6.2+支持，v6.0/v6.1不支持)
    r.set("test:get", "old_value")
    result = r.set("test:get", "new_value", get=True)
    results['SET_GET'] = result  # v6.2+返回b'old_value'，v6.0/v6.1返回None
    
    # 2. CLUSTER SHARDS 返回格式
    shards = r.execute_command('CLUSTER', 'SHARDS')
    results['CLUSTER_SHARDS'] = len(shards) > 0
    
    # 3. STREAM 相关命令 (v5+已有，v7有增强)
    try:
        r.xadd("test_stream", {"field": "value"})
        r.xrange("test_stream")
        results['STREAM'] = True
    except Exception as e:
        results['STREAM'] = False
    
    return results
```

#### 8.1.2 **EVALSHA / NOSCRIPT 验证（关键）**

> ⚠️ **重要**: 官方文档明确指出，Lua Script Cache **不是持久化资产**。重启或 failover 到 replica 后，应用侧可能需要重新加载脚本。

```python
def verify_evalsha_noscript(master_host, password=None):
    """验证 EVALSHA -> NOSCRIPT -> SCRIPT LOAD/EVAL fallback 场景
    
    这是升级后最容易踩坑的场景：
    - Redis 重启或 failover 后，脚本缓存会丢失
    - 应用使用 EVALSHA 会返回 NOSCRIPT 错误
    - 必须fallback到 SCRIPT LOAD 或 EVAL 重新加载脚本
    """
    r = redis.Redis(host=master_host, password=password)
    
    results = {}
    
    # 1. 加载一个测试脚本
    lua_script = "return redis.call('get', KEYS[1])"
    script_sha = r.script_load(lua_script)
    results['SCRIPT_LOAD'] = script_sha is not None
    
    # 2. 使用 EVALSHA 执行（应该成功）
    r.set("noscript:test", "value1")
    try:
        result = r.evalsha(script_sha, 1, "noscript:test")
        results['EVALSHA_SUCCESS'] = result == b'value1'
    except Exception as e:
        results['EVALSHA_SUCCESS'] = False
        results['EVALSHA_ERROR'] = str(e)
    
    # 3. 模拟脚本缓存丢失 - 使用不存在的 SHA 主动制造 NOSCRIPT
    # ⚠️ 重要：不要默认使用 SCRIPT FLUSH，它会清空全局脚本缓存
    # SCRIPT FLUSH 会改变服务器全局状态，可能影响其他测试线程
    # 推荐方式：使用一个从未加载过的 SHA
    fake_sha = "0123456789abcdef0123456789abcdef01234567"
    
    # 4. 再次使用 EVALSHA（应该失败，返回 NOSCRIPT）
    try:
        result = r.evalsha(fake_sha, 1, "noscript:test")
        results['NOSCRIPT_DETECTED'] = False  # 应该报错但没报
    except redis.ResponseError as e:
        results['NOSCRIPT_DETECTED'] = 'NOSCRIPT' in str(e).upper()
        results['NOSCRIPT_ERROR'] = str(e)
    
    # 3b. 真实场景验证：failover 后复测 EVALSHA fallback
    # 官方文档明确说 script cache 会在 failover 到 replica 后丢失
    # 这一步需要在实际 failover 场景中验证
    
    # 5. 验证 fallback 机制（应用应能自动处理）
    # 方式1: 使用 SCRIPT LOAD 重新获取 SHA
    new_sha = r.script_load(lua_script)
    result = r.evalsha(new_sha, 1, "noscript:test")
    results['FALLBACK_SCRIPT_LOAD'] = result == b'value1'
    
    # 方式2: 直接使用 EVAL
    result = r.eval(lua_script, 1, "noscript:test")
    results['FALLBACK_EVAL'] = result == b'value1'
    
    # 6. 测试 Redis 7 Functions（可选，Redis 7 新特性，更稳定）
    # Functions 是持久化的，重启后无需重新加载
    # ⚠️ 重要：在 Redis Cluster 环境下，Functions 需要管理员显式加载到所有 cluster nodes
    # 函数库会持久化到 AOF 并复制到 replicas，但不会自动分发到其他 master 节点
    # 客户端不会自动帮你完成加载，需要管理员手动在每个节点执行 FUNCTION LOAD
    try:
        # 创建简单的 function
        lua_code = """#!lua name=mylib
                    local function myfunc(keys, args)
                        return redis.call('get', keys[1])
                    end
                    redis.register_function('myfunc', myfunc)"""
        r.function_load(lua_code)
        
        # 使用 FCALL 调用
        # 语法: FCALL function_name numkeys [key ...] [arg ...]
        # numkeys 表示传入的 key 数量
        result = r.fcall("myfunc", 1, "noscript:test")  # 1个key
        results['REDIS7_FUNCTIONS'] = result == b'value1'
    except Exception as e:
        results['REDIS7_FUNCTIONS'] = False
        results['REDIS7_FUNCTIONS_ERROR'] = str(e)
    
    return results
```

**验证检查点：**

| 检查项 | 说明 |
|--------|------|
| SCRIPT_LOAD | SCRIPT LOAD 返回有效 SHA |
| EVALSHA_SUCCESS | 脚本缓存存在时 EVALSHA 正常工作 |
| NOSCRIPT_DETECTED | 脚本缓存清除后 EVALSHA 返回 NOSCRIPT |
| FALLBACK_SCRIPT_LOAD | 使用新 SHA 重试成功 |
| FALLBACK_EVAL | 使用 EVAL 直接执行成功 |
| REDIS7_FUNCTIONS | Redis 7 Functions 正常工作（可选） |

**⚠️ 重要提醒：**
1. **升级后必须验证应用的脚本fallback逻辑**
2. 如果应用使用连接池，确保连接被正确验证（可能需要 `CLIENT LIST` 或 `PING` 触发重置）
3. Redis 7 建议使用 Functions 代替临时脚本缓存（Functions 持久化、可复制）
4. **验证 NOSCRIPT 时不要默认使用 SCRIPT FLUSH**，它会清空全局脚本缓存，可能影响其他测试线程。推荐使用不存在的 SHA 主动制造 NOSCRIPT
5. **真实 failover 后复测**：官方文档明确说 script cache 会在 SCRIPT FLUSH、重启、failover 到 replica 后丢失，应在升级后的真实 failover 场景中复测 EVALSHA fallback

#### 8.1.3 数据结构编码验证

```python
def verify_data_encoding(master_host, password=None):
    """验证数据结构编码差异"""
    r = redis.Redis(host=master_host, password=password)
    
    results = {}
    
    # 1. HASH ziplist编码阈值变化
    for i in range(520):
        r.hset("test:hash", f"key{i}", f"value{i}")
    encoding = r.object("encoding", "test:hash")
    results['HASH_ENCODING'] = encoding  # v7使用listpack
    
    # 2. LIST quicklist编码
    for i in range(1000):
        r.lpush("test:list", f"value{i}")
    encoding = r.object("encoding", "test:list")
    results['LIST_ENCODING'] = encoding
    
    # 3. ZSET ziplist编码阈值
    for i in range(130):
        r.zadd("test:zset", {f"member{i}": i})
    encoding = r.object("encoding", "test:zset")
    results['ZSET_ENCODING'] = encoding
    
    return results
```

#### 8.1.4 复制兼容性验证

```python
def verify_replication_compatibility(master_host, slave_host, password=None):
    """验证v6从节点能正确复制v7主节点"""
    r_master = redis.Redis(host=master_host, password=password)
    r_slave = redis.Redis(host=slave_host, password=password)
    
    results = {}
    
    # 1. 写入测试
    for i in range(1000):
        r_master.set(f"compat:key{i}", f"value{i}")
    
    # 2. 等待复制
    time.sleep(2)
    
    # 3. 验证复制成功
    count = sum(1 for i in range(1000) 
                if r_slave.get(f"compat:key{i}") == f"value{i}".encode())
    results['REPLICATION_SYNC'] = count == 1000
    
    # 4. 验证RDB版本兼容性
    master_rdb_version = r_master.info('persistence').get('rdb_version')
    slave_rdb_version = r_slave.info('persistence').get('rdb_version')
    results['RDB_VERSION_CHECK'] = f"master:{master_rdb_version}, slave:{slave_rdb_version}"
    
    return results
```

### 8.2 验证脚本执行检查点

| 检查点 | 验证内容 | 判定标准 |
|--------|----------|----------|
| pre_check | 集群健康、版本确认 | cluster_state=ok |
| post_failover | 切主成功、新主正常 | role=master |
| replication_catchup | 复制追平 | offset一致 |
| command_compat | 命令兼容性 | 关键命令正常 |
| **evalsha_noscript** | **EVALSHA/NOSCRIPT/fallback** | **NOSCRIPT能正确检测并fallback成功** |
| data_integrity | 数据完整性 | 抽样key一致 |
| performance | 性能基线 | 延迟无明显增长 |

### 8.3 客户历史命令日志分析建议

建议在升级前分析客户历史command log，提取高频命令，重点验证：

1. 提取TOP 1000高频命令
2. 与Corner Cases列表比对
3. 针对高风险命令编写专项验证用例

#### 8.3.1 Lua 脚本语义兼容性测试（关键）

> ⚠️ **重要**：EVALSHA/NOSCRIPT 测的是缓存与 fallback，但**语义兼容性**测的是"脚本内部调用的命令在 v7 下结果是否一致"。

**推荐做法**：

1. **优先抽取客户真实 EVAL/EVALSHA 脚本样本做回放测试**
   - 从生产环境导出历史使用的 Lua 脚本
   - 在 v7 测试环境逐一执行
   - 对照 Section 6.4.3 的差异命令重点比对

2. **验证脚本内部命令的行为差异**
   - 某些命令在 v7 下可能有细微行为变化
   - 脚本中的 KEY/ARGV 处理可能受影响

3. **通用 demo 脚本补充**
   - 如果无法获取真实脚本，至少执行以下验证：
     - 基础读写操作脚本
     - 事务性脚本（MULTI/EXEC）
     - 计数器脚本（INCR/INCRBY）

```python
def verify_lua_semantic_compatibility(master_host, customer_scripts):
    """验证客户 Lua 脚本在 v7 上的语义兼容性
    
    优先使用真实客户脚本回放测试
    """
    r = redis.Redis(host=master_host)
    results = {}
    
    for script_name, lua_code in customer_scripts.items():
        try:
            # 直接执行脚本
            result = r.eval(lua_code, 0)
            results[script_name] = {'status': 'ok', 'result': result}
        except Exception as e:
            results[script_name] = {'status': 'error', 'error': str(e)}
    
    return results
```

---

## 9. 测试数据准备与压力测试

### 9.1 测试数据准备 (prepare_data.py)

#### 9.1.1 数据类型与数量

| 数据类型 | 数量 | Key格式 | 说明 |
|----------|------|---------|------|
| String | 1,000,000 | `test:string:000000` ~ `test:string:999999` | 随机长度10-200字节 |
| List | 100,000 | `test:list:000000` ~ `test:list:099999` | 每list含10个元素 |
| Hash | 100,000 | `test:hash:000000` ~ `test:hash:099999` | 每hash含20个字段 |
| Set | 10,000 | `test:set:000000` ~ `test:set:009999` | 每set含50个成员 |
| ZSet | 10,000 | `test:zset:000000` ~ `test:zset:009999` | 每zset含50个成员 |
| Stream | 1,000 | `test:stream:000000` ~ `test:stream:000999` | 每stream含5条消息 |
| HyperLogLog | 1,000 | `test:hll:000000` ~ `test:hll:000999` | 每hll含1000个元素 |
| Bitmap | 1,000 | `test:bitmap:000000` ~ `test:bitmap:000999` | 每bitmap含10位 |
| Geospatial | 1,000 | `test:geo:000000` ~ `test:geo:000999` | 含5个城市坐标 |
| Lua Script | 100 | 预加载到脚本缓存 | 7种不同脚本 |

> ⚠️ **重要 - Lua脚本验证**：当前仅预加载100个Lua脚本到缓存是**不够的**。必须验证：
> 1. **EVALSHA -> NOSCRIPT -> fallback** 场景（详见8.1.2节）
> 2. Redis重启或failover后脚本缓存会丢失
> 3. 建议在业务允许的情况下，升级到Redis 7 Functions（持久化、可复制）

#### 9.1.2 Key命名规范

所有测试数据采用统一格式：`test:{type}:{index:06d}`

示例：
- String: `test:string:000001`
- Hash: `test:hash:000100`
- Set: `test:set:005000`

#### 9.1.3 使用方法

```bash
# 使用默认数量（推荐）
python scripts/prepare_data.py --host 127.0.0.1 --port 7100 --all

# 自定义数量
python scripts/prepare_data.py --host 127.0.0.1 --port 7100 \
    --string 500000 --list 50000 --hash 50000

# 仅准备特定类型
python scripts/prepare_data.py --host 127.0.0.1 --port 7100 \
    --string 1000000 --script 100
```

#### 9.1.4 预期输出

```
============================================================
  Redis Test Data Preparation
  准备测试数据
============================================================

  Target: 127.0.0.1:7100

  Data counts:
    string: 1,000,000
    list: 100,000
    hash: 100,000
    set: 10,000
    zset: 10,000
    stream: 1,000
    hyperloglog: 1,000
    bitmap: 1,000
    geospatial: 1,000
    script: 100
    function: 10

  Connecting to Redis...
  ✓ Connected: Redis 6.2.18

============================================================
  Preparing data...
============================================================

============================================================
  Preparing STRINGS
  Prefix: test:string:*
  Count: 1,000,000
============================================================
    Progress: 10,000/1,000,000
    ...
    Progress: 1,000,000/1,000,000

  [After Strings] dbsize = 1,000,000
  ✓ Done: 1,000,000 strings in 120.5s (8298/s)

============================================================
  Summary
============================================================

  Total keys prepared: 1,221,000
  Total time: 180.5s
  Average: 6,763 keys/s
```

---

### 9.2 压力测试 (stress_test.py)

#### 9.2.1 支持的操作

| 数据类型 | 读操作 | 写操作 |
|----------|--------|--------|
| String | GET, STRLEN | SET, INCR, GETDEL |
| List | LRANGE, LLEN, LINDEX | LPUSH |
| Hash | HGETALL, HGET, HLEN | HSET |
| Set | SMEMBERS, SISMEMBER, SCARD | SADD |
| ZSet | ZRANGE, ZCARD, ZSCORE | ZADD |
| Stream | XRANGE, XLEN, XREAD | XADD |
| HyperLogLog | PFCOUNT | PFADD |
| Bitmap | GETBIT, BITCOUNT | SETBIT |
| Geospatial | GEOPOS, GEODIST, GEORADIUS | GEOADD |

#### 9.2.2 Lua脚本支持

压力测试启动时自动加载7个Lua脚本：

| 脚本名称 | 功能 |
|----------|------|
| script_get | 基本GET操作 |
| script_set | 基本SET操作 |
| script_incr | INCR操作 |
| script_del | DEL操作 |
| script_exists | EXISTS操作 |
| script_suffix | 获取值并添加后缀 |
| script_incrby | 原子递增 |

脚本通过`EVAL`和`EVALSHA`命令执行，权重设置为20以确保测试覆盖率。

> ⚠️ **重要 - EVALSHA/NOSCRIPT 测试**：压力测试必须包含以下场景：
> 1. **正常场景**：EVALSHA 执行成功
> 2. **NOSCRIPT 模拟**：使用不存在的 SHA 主动制造 NOSCRIPT（不要默认用 SCRIPT FLUSH，它会清空全局脚本缓存）
> 3. **Fallback 验证**：应用应能自动处理 NOSCRIPT，fallback 到 SCRIPT LOAD 或 EVAL
> 4. **真实 failover 后复测**：在实际 failover 场景中复测 EVALSHA fallback（脚本缓存在 failover 后会丢失）
> 5. **Redis 7 Functions**（可选）：测试 FCALL 是否正常工作

> **统一说明**：共享环境默认不用 SCRIPT FLUSH，优先用不存在的 SHA 制造 NOSCRIPT；真实 failover 后再复测一次 EVALSHA fallback。

#### 9.2.3 操作权重

压力测试按数据量比例分配操作权重：

| 数据类型 | 数量 | 权重 | 说明 |
|----------|------|------|------|
| string | 1,000,000 | 1000 | 最高频 |
| list | 100,000 | 100 | |
| hash | 100,000 | 100 | |
| set | 10,000 | 10 | |
| zset | 10,000 | 10 | |
| stream | 1,000 | 1 | |
| hll | 1,000 | 1 | |
| bitmap | 1,000 | 1 | |
| geo | 1,000 | 1 | |
| script | 100 | 20 | 固定权重确保测试 |

#### 9.2.4 使用方法

```bash
# 使用节点列表（默认参数与prepare_data.py一致）
python scripts/stress_test.py \
    --nodes "127.0.0.1:7000,127.0.0.1:7001,127.0.0.1:7002" \
    --qps 1000 --duration 300

# 自定义数据量范围（需与prepare_data.py保持一致）
python scripts/stress_test.py \
    --nodes "127.0.0.1:7000,127.0.0.1:7001,127.0.0.1:7002" \
    --string 1000000 --list 100000 --hash 100000 \
    --set 10000 --zset 10000 \
    --stream 1000 --hll 1000 --bitmap 1000 --geo 1000 \
    --qps 1000 --duration 300

# 使用配置文件
python scripts/stress_test.py \
    --config cluster_config.json \
    --qps 2000 --duration 600

# 交互模式（等待用户确认开始）
python scripts/stress_test.py \
    --nodes "127.0.0.1:7000" \
    --qps 500 --interactive

# 指定密码
python scripts/stress_test.py \
    --nodes "127.0.0.1:7000" \
    --password your_password \
    --qps 1000
```

**参数说明:**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| --nodes/-n | - | 节点列表，格式: host:port,host:port,... |
| --qps/-q | 1000 | 目标QPS |
| --duration/-d | 300 | 测试持续时间（秒） |
| --key-prefix/-k | test | key前缀，需与prepare_data.py保持一致 |
| --string/-s | 1000000 | String key数量 |
| --list/-l | 100000 | List key数量 |
| --hash | 100000 | Hash key数量 |
| --set | 10000 | Set key数量 |
| --zset | 10000 | ZSet key数量 |
| --stream | 1000 | Stream key数量 |
| --hll | 1000 | HyperLogLog key数量 |
| --bitmap | 1000 | Bitmap key数量 |
| --geo | 1000 | Geo key数量 |

**注意:** stress_test.py的key范围必须与prepare_data.py保持一致，确保测试时key存在。例如prepare_data.py使用`--string 1000000`生成`test:string:0`到`test:string:999999`，则stress_test.py也需使用`--string 1000000`使随机key落在有效范围内。

#### 9.2.5 预期输出

```
============================================================
  Redis Client Stress Test
  模拟客户端在failover期间的读写
============================================================

  Using 2 nodes from command line
  Target QPS: 1000
  Duration: 300s
  Key prefix: stress_test

  Loading Lua scripts...
    Loaded: script_get (SHA: abc12345...)
    Loaded: script_set (SHA: def67890...)
    ...
  ✓ Loaded 7 scripts

  [Before Stress Test] dbsize = 1,221,000

  Starting stress test with 10 threads, ~100 ops/sec each
  (Press Ctrl+C to stop)

  [10s] cmds=10023, success=10015, failed=8, rate=99.9%, errors=1
  [20s] cmds=20045, success=20038, failed=7, rate=99.9%, errors=1
  ...

============================================================
  Test Results
============================================================

  Total time: 300.45s
  Total commands: 300,456
  Success: 300,380
  Failed: 76
  Success rate: 99.97%

  Error periods: 3
  Total error time: 2.34s

  Error period details:
    [1] 1.25s, 45 errors
    [2] 0.85s, 28 errors
    [3] 0.24s, 3 errors

============================================================
  KEY METRICS FOR FAILOVER TEST
============================================================
  Error duration: 2.34s
  Error count: 76
  Error periods: 3

  Results saved to: stress_test_result.json
```

---

## 10. 附录：命令速查表 (Cluster模式)

```bash
# 新增从库 (需要先获取主节点ID)
redis-cli -h <master_node> CLUSTER NODES | grep master
redis-cli -h <new_node> CLUSTER REPLICATE <master_node_id>

# 从节点提升为主
redis-cli -h <slave_node> CLUSTER FAILOVER

# 降为从库 (需要先获取新主节点ID)
redis-cli -h <master_node> CLUSTER NODES | grep master
redis-cli -h <master_node> CLUSTER REPLICATE <new_master_node_id>

# 查看复制状态
redis-cli -h <node> INFO replication

# 查看集群状态
redis-cli -h <node> CLUSTER INFO

# 查看集群节点
redis-cli -h <node> CLUSTER NODES
```
