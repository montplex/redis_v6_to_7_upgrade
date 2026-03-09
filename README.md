# Redis v6 → v7 升级工具

本项目提供 Redis Cluster 从 6.2.x 升级到 7.2.x LTS 的完整方案和脚本工具。

## 项目结构

```
.
├── bin/                    # Redis 可执行文件
│   ├── redis-server-v6    # Redis 6.2.x 服务端
│   ├── redis-server-v7    # Redis 7.2.x 服务端
│   └── redis-cli          # Redis 命令行客户端
├── scripts/               # 升级脚本目录
├── design.md              # 升级方案设计文档
├── test_config.json       # 测试配置
```

## 文档说明

| 文件 | 说明 |
|------|------|
| **design.md** | 升级方案设计文档，包含架构概述、升级前检查清单、详细升级流程、回滚方案等 |
| **scripts/guide.md** | 逐步升级指南，提供每个升级步骤的命令示例和验证要点 |
| **scripts/*.py** | 各步骤的 Python 自动化脚本 |
| **test_config.json** | 测试环境配置文件 |

## 快速开始

详见 [scripts/guide.md](scripts/guide.md)

## 核心升级流程

1. **Step 0**: 创建 v6 集群环境
2. **Step 1**: 准备测试数据
3. **Step 2**: 升级前检查与配置调整
4. **Step 3**: 添加 v7 从节点
5. **Step 4**: 验证主从复制同步
6. **Step 5**: 压力测试（可选）
7. **Step 6**: Failover 切换到 v7 主节点
8. **Step 12**: 移除 v6 节点，升级完成
