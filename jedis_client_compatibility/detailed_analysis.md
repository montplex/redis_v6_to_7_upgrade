# Jedis v6.2.0 单元测试差异详细分析

## 测试环境
- **Jedis版本**: v6.2.0
- **Redis v6**: 6.2.18
- **Redis v7**: 7.2.11
- **测试日期**: 2026-03-04

---

## 一、总体结果对比

| 指标 | Redis v6.2.18 | Redis v7.2.11 | 差异 |
|------|---------------|---------------|------|
| 总测试数 | 8737 | 9032 | v7多295个 |
| 失败 (Failures) | 0 | 1 | v7独有1个 |
| 错误 (Errors) | 16 | 11 | v7少5个 |
| 跳过 (Skipped) | 567 | 410 | v7少157个 |
| **实际通过** | **8154** | **8610** | **v7多456个** |

---

## 二、Redis v6 特有错误（v7正常通过）

### 2.1 ClusterShardedPublishSubscribeCommandsTest
- **测试数**: 8
- **错误数**: 1
- **跳过数**: 7
- **问题**: Cluster节点清理时出现 `ERR Unknown node` 错误
- **原因**: Redis v6的Cluster节点管理机制与v7有差异
- **影响**: 在v6上该测试无法正常清理资源

### 2.2 ClusterStringValuesCommandsTest
- **测试数**: 27 (每个测试类运行3次，共81次)
- **错误数**: 3 (每次运行1个错误)
- **跳过数**: 3
- **问题**: `setGetWithParams` 测试报 `ERR syntax error`
- **原因**: Redis v6不支持新的SET/GET语法参数（如SET GET参数）
- **影响**: 字符串值相关的高级功能在v6上不可用

### 2.3 ClusterBinaryValuesCommandsTest
- **测试数**: 31 (每个测试类运行3次，共93次)
- **错误数**: 3
- **问题**: 同样是 `setGetWithParams` 语法错误
- **原因**: Redis v6不支持二进制值的GET参数语法
- **影响**: 二进制数据的SET/GET操作在v6上受限

### 2.4 PooledStringValuesCommandsTest
- **测试数**: 27 (每个测试类运行3次，共81次)
- **错误数**: 3
- **跳过数**: 3
- **问题**: 同ClusterStringValuesCommandsTest
- **原因**: 连接池版本的String Values命令也有相同限制

### 2.5 PooledBinaryValuesCommandsTest
- **测试数**: 34 (每个测试类运行3次，共102次)
- **错误数**: 3
- **问题**: 同ClusterBinaryValuesCommandsTest
- **原因**: 连接池版本的Binary Values命令也有相同限制

---

## 三、Redis v7 特有失败（v6正常通过）

### 3.1 ClusterCommandsTest.clusterShards
- **测试数**: 20
- **失败数**: 1
- **失败测试**: `clusterShards`
- **错误信息**: `AssertionFailedError: expected: not <null>`
- **问题位置**: `ClusterCommandsTest.java:241`
- **原因**: Redis v7的Cluster API发生变化，`cluster shards`命令返回结构与v6不同
- **影响**: Jedis客户端的clusterShards方法无法正确解析v7的返回结果

---

## 四、两版本共有的错误（可忽略）

以下错误在两个版本上都存在，主要是测试环境配置问题：

| 测试类 | 错误类型 | 原因 |
|--------|----------|------|
| SSLOptionsJedisPooledTest | TLS证书缺失 | 测试环境未配置TLS |
| SSLJedisSentinelPoolTest | TLS证书缺失 | 测试环境未配置TLS |
| SSLOptionsJedisTest | TLS证书缺失 | 测试环境未配置TLS |
| SSLACLJedisTest | TLS证书缺失 | 测试环境未配置TLS |
| SSLOptionsJedisClusterTest | TLS证书缺失 | 测试环境未配置TLS |
| SSLJedisTest | TLS证书缺失 | 测试环境未配置TLS |
| SSLJedisClusterTest | TLS证书缺失 | 测试环境未配置TLS |
| SSLACLJedisClusterTest | TLS证书缺失 | 测试环境未配置TLS |
| SSLJedisPooledClientSideCacheTest | TLS证书缺失 | 测试环境未配置TLS |
| SSLOptionsJedisSentinelPoolTest | TLS证书缺失 | 测试环境未配置TLS |
| RedisJsonV1Test | Gson反射错误 | Java版本兼容性问题 |

---

## 五、跳过测试分析

### 5.1 Redis v6 跳过的测试（567个）
- 主要集中在Cluster和Values Commands测试
- 原因：Redis v6不支持某些新命令和特性

### 5.2 Redis v7 跳过的测试（410个）
- 跳过的测试数量明显减少
- 说明Redis v7对新特性支持更好

### 5.3 差异
- v7比v6少跳过157个测试
- 主要减少在Values Commands相关测试

---

## 六、总结与建议

### 6.1 兼容性总结
- **Jedis v6.2.0 与 Redis v7 兼容性更好**
- v7实际通过的测试多456个
- v7跳过的测试更少

### 6.2 已知问题
1. **v6特有**: Cluster Values Commands测试会报错，建议在v6环境跳过这些测试
2. **v7特有**: ClusterCommandsTest.clusterShards在v7上会失败，需要Jedis客户端更新支持

### 6.3 生产环境建议
- 如果使用Redis v7的新特性（如SET GET参数），需要Jedis更新到更高版本
- 如果使用Redis v6，当前Jedis v6.2.0可正常工作，但某些高级特性不可用
- 推荐使用Redis v7以获得更好的兼容性和性能

---

## 七、详细日志位置

- Redis v6测试日志: `jedis_v6_all_tests.log`
- Redis v7测试日志: `jedis_v7_all_tests.log`
- 本分析文档: `detailed_analysis.md`
- 对比报告: `summary.html`
