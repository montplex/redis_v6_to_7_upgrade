#!/usr/bin/env python3
"""
Master Upgrade Script - 执行所有升级步骤
根据 is_do_rollback 参数决定执行正常流程或回滚流程

Normal flow: Step 0 → 1 → 2 → 2.5 → 3 → 4 → 5 → 6 → (observation) → Step 12
Rollback flow: Step 0 → 1 → 2 → 2.5 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12

Usage:
    python run_upgrade.py --config upgrade_config.json
    python run_upgrade.py --config upgrade_config.json --rollback
    python run_upgrade.py --config upgrade_config.json --do-rollback true
"""

import sys
import os
import argparse
import subprocess
import time
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config(config_path):
    """加载配置文件"""
    config_file = os.path.join(SCRIPT_DIR, config_path)
    if not os.path.exists(config_file):
        print(f"  ERROR: Config file not found: {config_file}")
        return None
    with open(config_file, 'r') as f:
        return json.load(f)


def get_master_host_port(config):
    """获取第一个master的host和port"""
    shards = config.get('shards', [])
    if shards:
        master = shards[0].get('master', {})
        return master.get('host', '127.0.0.1'), master.get('port', 7000)
    return '127.0.0.1', 7000


def get_nodes_from_config(config):
    """从配置中获取节点列表"""
    nodes = config.get('nodes', [])
    if nodes:
        return ','.join(f"{n['host']}:{n['port']}" for n in nodes)
    
    shards = config.get('shards', [])
    node_set = set()
    for shard in shards:
        master = shard.get('master', {})
        if master.get('host') and master.get('port'):
            node_set.add(f"{master['host']}:{master['port']}")
        for slave in shard.get('slaves', []):
            if slave.get('host') and slave.get('port'):
                node_set.add(f"{slave['host']}:{slave['port']}")
    return ','.join(sorted(node_set))


def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_step(step_num, description):
    print(f"\n{'='*70}")
    print(f"  Step {step_num}: {description}")
    print(f"{'='*70}")


def run_script_background(script_name, args=None, cwd=None):
    """后台运行脚本，返回subprocess对象"""
    if cwd is None:
        cwd = SCRIPT_DIR
    
    cmd = [sys.executable, script_name]
    if args:
        cmd.extend(args)
    
    print(f"  Starting in background: {' '.join(cmd)}")
    
    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    return process


def wait_for_process(process, timeout=None):
    """等待后台进程完成"""
    try:
        stdout, _ = process.communicate(timeout=timeout)
        return process.returncode, stdout
    except subprocess.TimeoutExpired:
        process.kill()
        return -1, "Timeout"


def run_script(script_name, args=None, cwd=None, expect_ok=True, auto_input=None, step_num=None, step_desc=None):
    """运行脚本并验证结果
    
    Args:
        script_name: 脚本名称
        args: 脚本参数
        cwd: 工作目录
        expect_ok: 是否期望成功
        auto_input: 自动输入的字符串（如 'y\n' 用于自动确认）
        step_num: 步骤编号（用于日志文件命名）
        step_desc: 步骤描述（用于日志文件命名）
    
    Returns:
        bool: 是否符合预期
    """
    if cwd is None:
        cwd = SCRIPT_DIR
    
    cmd = [sys.executable, script_name]
    if args:
        cmd.extend(args)
    
    print(f"  Running: {' '.join(cmd)}")
    
    log_file = None
    log_path = None
    if step_num is not None:
        log_dir = os.path.join(SCRIPT_DIR, '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        safe_desc = step_desc.replace(' ', '_').replace('/', '_') if step_desc else 'unknown'
        log_path = os.path.join(log_dir, f'step{step_num}_{safe_desc}.output.log')
        log_file = open(log_path, 'w')
        log_file.write(f"Command: {' '.join(cmd)}\n")
        log_file.write("=" * 70 + "\n")
    
    input_data = auto_input if auto_input else None
    
    if input_data:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True
        )
        stdout, _ = process.communicate(input=input_data)
        output_lines = stdout.splitlines(keepends=True)
        for line in output_lines:
            print(line, end='')
            if log_file:
                log_file.write(line)
        process.wait()
        output = stdout
    else:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        output_lines = []
        while True:
            line = process.stdout.readline()
            if not line:
                break
            print(line, end='')
            output_lines.append(line)
            if log_file:
                log_file.write(line)
        
        process.wait()
        output = ''.join(output_lines)
    
    if log_file:
        log_file.write("\n" + "=" * 70 + "\n")
        log_file.write(f"Exit code: {process.returncode}\n")
        log_file.close()
        print(f"  Log saved to: {log_path}")
    
    if '✓ PASS' in output:
        print(f"  ✓ PASS - Script completed successfully")
        return True
    elif '✗ FAIL' in output:
        print(f"  ✗ FAIL - Script reported failure")
        return False
    elif process.returncode != 0:
        print(f"  ✗ FAIL - Script failed with code {process.returncode}")
        print(f"  Output: {output[-500:]}")
        return False
    elif not expect_ok:
        print(f"  ✓ Script completed (expected potential issues)")
        return True
    else:
        print(f"  ⚠ Script completed but no clear PASS/FAIL indicator")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Redis v6 to v7 Upgrade Master Script"
    )
    parser.add_argument(
        '--config', '-c',
        default='upgrade_config.json',
        help='升级配置文件路径'
    )
    parser.add_argument(
        '--do-rollback', '-r',
        type=lambda x: x.lower() == 'true',
        default=False,
        help='是否执行回滚流程 (default: false)'
    )
    parser.add_argument(
        '--skip-steps',
        default='',
        help='跳过的步骤，逗号分隔，如: 1,2,5'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅显示要执行的步骤，不实际执行'
    )
    parser.add_argument(
        '--auto-continue',
        action='store_true',
        help='自动确认继续，不等待用户输入（用于failover等交互步骤）'
    )
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    if not config:
        print("  ERROR: Failed to load config")
        return
    
    master_host, master_port = get_master_host_port(config)
    nodes = get_nodes_from_config(config)
    
    skip_steps = set()
    if args.skip_steps:
        skip_steps = set(int(s) for s in args.skip_steps.split(','))
    
    print_header("Redis v6 to v7 Upgrade")
    print(f"  Config: {args.config}")
    print(f"  Master: {master_host}:{master_port}")
    print(f"  Rollback: {args.do_rollback}")
    print(f"  Skip steps: {skip_steps if skip_steps else 'None'}")
    
    if args.dry_run:
        print("\n  [DRY RUN MODE - No actual execution]")
    
    if args.do_rollback:
        print("\n  Executing ROLLBACK FLOW:")
        print("  Step 0 → 1 → 2 → 2.5 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12")
    else:
        print("\n  Executing NORMAL FLOW:")
        print("  Step 0 → 1 → 2 → 2.5 → 3 → 4 → 5 → 6 → (observation) → 12")
    
    if args.dry_run:
        print("\n  Steps to execute:")
        steps = get_steps_to_execute(args.do_rollback, skip_steps)
        for step in steps:
            print(f"    Step {step}")
        return
    
    if not confirm("\n  Continue?", args.auto_continue):
        print("  Aborted.")
        return
    
    steps = get_steps_to_execute(args.do_rollback, skip_steps)
    
    for step in steps:
        step_desc = ""
        if step == 0:
            print_step(0, "准备集群")
            step_desc = "0_prepare_cluster"
            print("  (Cluster should already be running)")
        
        elif step == 1:
            print_step(1, "准备测试数据")
            step_desc = "1_prepare_data"
            run_script('prepare_data.py', ['--host', master_host, '--port', str(master_port), '--all'], step_num=step, step_desc=step_desc)
        
        elif step == 2:
            print_step(2, "升级前检查")
            step_desc = "2_pre_upgrade_check"
            run_script('pre_upgrade_check.py', ['--config', args.config, '--skip-warnings'], auto_input='yes\n', step_num=step, step_desc=step_desc)
        
        elif step == 2.5:
            print_step(2.5, "调整v6 masters复制缓冲区")
            step_desc = "2.5_adjust_buffers"
            run_script('adjust_replication_buffers.py', ['--config', args.config, '--step', '2.5', '--auto-continue'], auto_input='yes\n', step_num=step, step_desc=step_desc)
        
        elif step == 3:
            print_step(3, "添加v7从节点")
            step_desc = "3_add_v7_replica"
            run_script('add_v7_replica.py', ['--config', args.config], step_num=step, step_desc=step_desc)
        
        elif step == 4:
            print_step(4, "验证复制状态")
            step_desc = "4_verify_replication"
            run_script('verify_replication.py', ['--config', args.config], step_num=step, step_desc=step_desc)
        
        elif step == 5:
            print_step(5, "压力测试")
            step_desc = "5_stress_test"
            run_script('stress_test.py', [
                '--nodes', nodes,
                '--qps', '1000',
                '--duration', '30'
            ], step_num=step, step_desc=step_desc)
        
        elif step == 6:
            print_step(6, "Failover到v7 (同时运行压力测试)")
            step_desc = "6_failover_to_v7"
            
            print("\n  [1] Starting stress test in background...")
            stress_proc = run_script_background('stress_test.py', [
                '--nodes', nodes,
                '--qps', '1000',
                '--duration', '120'
            ])
            
            print("\n  [2] Running failover...")
            auto_input = 'yes\n' if args.auto_continue else None
            failover_result = run_script('failover_to_v7.py', ['--config', args.config, '--auto-continue'], auto_input=auto_input, step_num=step, step_desc=step_desc)
            
            print("\n  [3] Waiting for stress test to complete...")
            returncode, stdout = wait_for_process(stress_proc, timeout=180)
            
            if '✓ PASS' in stdout:
                print("  ✓ Stress test PASSED during failover")
            elif '✗ FAIL' in stdout:
                print("  ✗ Stress test FAILED during failover")
            else:
                print(f"  ⚠ Stress test completed with code {returncode}")
            
            print("\n  Stress test output (last 30 lines):")
            lines = stdout.split('\n')
            for line in lines[-30:]:
                print(f"    {line}")
        
        elif step == 7:
            print_step(7, "回滚到v6")
            step_desc = "7_rollback_to_v6"
            auto_input = 'yes\n' if args.auto_continue else None
            run_script('rollback.py', ['--config', args.config], auto_input=auto_input, step_num=step, step_desc=step_desc)
        
        elif step == 8:
            print_step(8, "验证回滚后复制状态")
            step_desc = "8_verify_rollback"
            run_script('verify_replication.py', [
                '--config', args.config,
                '--mode', 'post-rollback'
            ], step_num=step, step_desc=step_desc)
        
        elif step == 9:
            print_step(9, "压力测试(回滚后)")
            step_desc = "9_stress_test_after_rollback"
            run_script('stress_test.py', [
                '--nodes', nodes,
                '--qps', '1000',
                '--duration', '30'
            ], step_num=step, step_desc=step_desc)
        
        elif step == 10:
            print_step(10, "重新Failover到v7")
            step_desc = "10_refailover_to_v7"
            auto_input = 'yes\n' if args.auto_continue else None
            run_script('failover_to_v7.py', ['--config', args.config], auto_input=auto_input, step_num=step, step_desc=step_desc)
        
        elif step == 11:
            print_step(11, "验证复制状态")
            step_desc = "11_verify_post_failover"
            run_script('verify_replication.py', [
                '--config', args.config,
                '--mode', 'post-failover'
            ], step_num=step, step_desc=step_desc)
        
        elif step == 12:
            print_step(12, "移除v6节点")
            step_desc = "12_remove_v6_nodes"
            run_script('remove_v6_nodes.py', ['--config', args.config, '--auto-continue'], step_num=step, step_desc=step_desc)
    
    print_header("UPGRADE COMPLETED" if not args.do_rollback else "ROLLBACK COMPLETED")


def get_steps_to_execute(do_rollback, skip_steps):
    """获取要执行的步骤列表"""
    if do_rollback:
        return [s for s in [0, 1, 2, 2.5, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] if s not in skip_steps]
    else:
        normal_steps = [0, 1, 2, 2.5, 3, 4, 5, 6, 12]
        return [s for s in normal_steps if s not in skip_steps]


def confirm(prompt, auto_continue=False):
    """确认提示"""
    if auto_continue:
        print(f"\n{prompt} [y/N]: y (auto-confirmed)")
        return True
    response = input(f"\n{prompt} [y/N]: ")
    return response.lower() in ('y', 'yes')


if __name__ == '__main__':
    main()
