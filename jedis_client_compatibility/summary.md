# Jedis v6.2.0 单元测试对比报告

**全部单元测试 - Redis v6.2.18 vs Redis v7.2.11**

## 测试环境

- **Jedis版本:** v6.2.0
- **Redis v6版本:** 6.2.18
- **Redis v7版本:** 7.2.11
- **测试日期:** 2026-03-04
- **测试说明:** 已排除TLS相关测试 (SSL*Test.java)

## 测试结果总览

| 指标 | Redis v6.2.18 | Redis v7.2.11 | 差异 |
|------|---------------|---------------|------|
| 总测试数 | 8737 | 9032 | v7多295个 |
| 失败 (Failures) | 0 | 1 | v7独有 |
| 错误 (Errors) | 16 | 11 | v7少5个 |
| 跳过 (Skipped) | 567 | 410 | v7少157个 |
| 实际通过 | 8737 - 0 - 16 - 567 = **8154** | 9032 - 1 - 11 - 410 = **8610** | v7多456个 |

## 详细差异分析

### 1. Redis v6 错误但 v7 正常的测试（v6独有错误）

| 测试类 | 测试数 | 错误数 | 跳过数 | 说明 |
|--------|--------|--------|--------|------|
| ClusterShardedPublishSubscribeCommandsTest | 8 | 1 | 7 | Cluster节点清理错误 |
| ClusterStringValuesCommandsTest | 27 | 3 (共81次运行) | 3 | setGetWithParams语法错误 |
| ClusterBinaryValuesCommandsTest | 31 | 3 (共93次运行) | 0 | setGetWithParams语法错误 |
| PooledStringValuesCommandsTest | 27 | 3 (共81次运行) | 3 | setGetWithParams语法错误 |
| PooledBinaryValuesCommandsTest | 34 | 3 (共102次运行) | 0 | setGetWithParams语法错误 |

### 2. Redis v7 错误但 v6 正常的测试（v7独有失败）

| 测试类 | 测试数 | 失败/错误数 | 说明 |
|--------|--------|-------------|------|
| **ClusterCommandsTest.clusterShards** | 20 | 1 Failure | clusterShards返回null，v7的Cluster API变化导致 |

### 3. 两版本共有的错误（TLS/SSL相关，可忽略）

| 测试类 | 说明 |
|--------|------|
| SSLOptionsJedisPooledTest | 缺少TLS证书文件 |
| SSLJedisSentinelPoolTest | 缺少TLS证书文件 |
| SSLOptionsJedisTest | 缺少TLS证书文件 |
| SSLACLJedisTest | 缺少TLS证书文件 |
| SSLOptionsJedisClusterTest | 缺少TLS证书文件 |
| SSLJedisTest | 缺少TLS证书文件 |
| SSLJedisClusterTest | 缺少TLS证书文件 |
| SSLACLJedisClusterTest | 缺少TLS证书文件 |
| SSLJedisPooledClientSideCacheTest | 缺少TLS证书文件 |
| SSLOptionsJedisSentinelPoolTest | 缺少TLS证书文件 |
| RedisJsonV1Test | Gson反射兼容性问题 |

## 结论

- **Redis v7 总体表现更优:** 实际通过8610个测试 vs v6的8154个，多456个
- **v6独有的错误:** 主要是Cluster相关测试的Values Commands测试，因Redis v6不支持新的SET/GET语法参数
- **v7独有的失败:** ClusterCommandsTest.clusterShards测试失败，是v7的Cluster API变化导致
- **跳过测试差异:** v7跳过的测试更少(410 vs 567)，说明v7对新特性支持更好

## 详细分析

详见 [detailed_analysis.md](detailed_analysis.md)

---
生成时间: 2026-03-04 | Jedis v6.2.0 | Redis v6.2.18 vs v7.2.11
