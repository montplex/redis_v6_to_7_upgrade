#!/usr/bin/env python3
"""
Step 2.5 / Step 6.5: 调整复制缓冲区脚本

使用场景:
- Step 2.5: 在添加 v7 从节点之前，调整 v6 masters 的复制缓冲区
- Step 6.5: 在 failover 后，调整新 v7 masters 的复制缓冲区

原因:
- 在 v6 master → v7 replica 的接入过程中，增大 backlog / output buffer 可以让全量同步过程更稳定
- 真正 mixed-version 的高风险窗口，是 Step 6 之后 v7 master → v6 replicas 还在挂着观察期的时候
- Redis 复制文档明确写了：链路断开后，replica 会先尝试 partial resync；
  如果 backlog 不够或 replication ID 历史不匹配，就会退化成 full resync
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    RedisNode, print_header, print_section, print_status, print_expect,
    load_config, confirm_action
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Step 2.5/6.5: Adjust Replication Buffers - 调整复制缓冲区"
    )
    parser.add_argument(
        '--config', '-c',
        default='upgrade_config.json',
        help='升级配置文件路径'
    )
    parser.add_argument(
        '--step',
        choices=['2.5', '6.5', 'both'],
        default='both',
        help='执行哪个步骤: 2.5=v6 masters, 6.5=v7 masters, both=两者都执行'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅模拟操作，不实际执行'
    )
    parser.add_argument(
        '--auto-continue',
        action='store_true',
        help='自动确认继续，不等待用户输入'
    )
    return parser.parse_args()


def adjust_buffer_on_node(node_host, node_port, password=None, step_name=""):
    """在单个节点上调整复制缓冲区"""
    print(f"\n  Adjusting buffer on {node_host}:{node_port} ({step_name})...")
    
    node = RedisNode(host=node_host, port=node_port, password=password)
    
    if not node.ping():
        print_status(f"Node {node_port}", "not responding", "FAIL")
        return False
    
    success = True
    
    # 1. 设置 repl-backlog-size
    try:
        result = node.execute_command('CONFIG', 'SET', 'repl-backlog-size', '256mb')
        print_status(f"repl-backlog-size", "256mb", "OK")
    except Exception as e:
        print_status(f"repl-backlog-size", str(e), "FAIL")
        success = False
    
    # 2. 设置 client-output-buffer-limit slave (注意: Redis 使用 "slave" 而非 "replica")
    try:
        result = node.execute_command('CONFIG', 'SET', 'client-output-buffer-limit', 'slave 512mb 64mb 60')
        print_status(f"client-output-buffer-limit", "512mb 64mb 60", "OK")
    except Exception as e:
        print_status(f"client-output-buffer-limit", str(e), "FAIL")
        success = False
    
    # 3. CONFIG REWRITE
    try:
        result = node.execute_command('CONFIG', 'REWRITE')
        print_status(f"CONFIG REWRITE", "saved to redis.conf", "OK")
    except Exception as e:
        # 检查是否是非配置文件启动的情况
        err_str = str(e).lower()
        if 'using an immutable image' in err_str or 'configmap' in err_str or \
           'no such file' in err_str or 'permission denied' in err_str:
            print_status(f"CONFIG REWRITE", "not using writable conf (skip)", "WARN")
            print(f"    Note: If using immutable image/ConfigMap, persist via config management")
        else:
            print_status(f"CONFIG REWRITE", str(e), "WARN")
    
    return success


def adjust_v6_masters(shards, config, args):
    """Step 2.5: 在 v6 masters 上调整缓冲区"""
    print_header("Step 2.5: Adjust Buffers on v6 Masters")
    print("  Context: Before adding v7 replicas")
    print("  Purpose: Make v6→v7 sync more stable\n")
    
    if not args.dry_run:
        if not args.auto_continue:
            if not confirm_action("Proceed with adjusting v6 masters?"):
                print("Aborted.")
                return []
    
    results = []
    
    for shard in shards:
        shard_idx = shard.get('shard_index', 0) + 1
        master = shard.get('master', {})
        master_host = master.get('host')
        master_port = master.get('port')
        
        if not master_host or not master_port:
            continue
        
        print_section(f"Shard {shard_idx}: v6 Master {master_host}:{master_port}")
        
        if args.dry_run:
            print_status("DRY RUN", "would adjust buffer on v6 master", "INFO")
            results.append({'host': master_host, 'port': master_port, 'status': 'dry_run'})
        else:
            success = adjust_buffer_on_node(
                master_host, master_port, 
                config.get('master_password'),
                "v6 master"
            )
            results.append({
                'host': master_host, 
                'port': master_port, 
                'status': 'ok' if success else 'failed'
            })
    
    return results


def adjust_v7_masters(shards, config, args):
    """Step 6.5: 在 v7 masters 上调整缓冲区"""
    print_header("Step 6.5: Adjust Buffers on v7 Masters")
    print("  Context: After failover, protecting v6 replicas")
    print("  Purpose: Prevent full resync when v7 master → v6 replicas\n")
    
    if not args.dry_run:
        if not args.auto_continue:
            if not confirm_action("Proceed with adjusting v7 masters?"):
                print("Aborted.")
                return []
    
    results = []
    
    for shard in shards:
        shard_idx = shard.get('shard_index', 0) + 1
        
        # 找到当前的 v7 master (在 new_slaves 中找第一个)
        new_slaves = shard.get('new_slaves', [])
        v7_master = None
        
        for slave in new_slaves:
            if slave.get('host'):
                v7_master = {
                    'host': slave.get('host'),
                    'port': slave.get('port', 6379)
                }
                break
        
        if not v7_master:
            print_status(f"Shard {shard_idx}", "no v7 master found", "WARN")
            continue
        
        print_section(f"Shard {shard_idx}: v7 Master {v7_master['host']}:{v7_master['port']}")
        
        if args.dry_run:
            print_status("DRY RUN", "would adjust buffer on v7 master", "INFO")
            results.append({'host': v7_master['host'], 'port': v7_master['port'], 'status': 'dry_run'})
        else:
            success = adjust_buffer_on_node(
                v7_master['host'], v7_master['port'],
                config.get('master_password'),
                "v7 master"
            )
            results.append({
                'host': v7_master['host'],
                'port': v7_master['port'],
                'status': 'ok' if success else 'failed'
            })
    
    return results


def main():
    args = parse_args()
    
    print_header("Step 2.5 / 6.5: Adjust Replication Buffers")
    print(f"  Config: {args.config}")
    print(f"  Step: {args.step}")
    print(f"  Dry run: {args.dry_run}")
    
    # 加载配置
    config = load_config(args.config)
    if not config:
        print_status("ERROR", f"Cannot load config from {args.config}", "FAIL")
        sys.exit(1)
    
    shards = config.get('shards', [])
    
    if not shards:
        print_status("ERROR", "No shards found in config", "FAIL")
        sys.exit(1)
    
    print(f"  Processing {len(shards)} shard(s)")
    
    all_results = []
    
    # Step 2.5: 调整 v6 masters
    if args.step in ('2.5', 'both'):
        results = adjust_v6_masters(shards, config, args)
        all_results.extend(results)
    
    # Step 6.5: 调整 v7 masters
    if args.step in ('6.5', 'both'):
        results = adjust_v7_masters(shards, config, args)
        all_results.extend(results)
    
    # 打印摘要
    print_header("Buffer Adjustment Summary")
    
    total_ok = sum(1 for r in all_results if r.get('status') == 'ok')
    total_failed = sum(1 for r in all_results if r.get('status') == 'failed')
    
    print(f"  Total: {total_ok} adjusted, {total_failed} failed")
    
    print("\n" + "=" * 60)
    if total_failed == 0:
        print("  ✓ PASS - All buffers adjusted successfully")
    else:
        print(f"  ✗ FAIL - {total_failed} adjustment(s) failed")
    print("=" * 60)


if __name__ == '__main__':
    main()
