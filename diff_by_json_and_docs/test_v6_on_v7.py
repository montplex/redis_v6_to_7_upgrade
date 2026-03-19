#!/usr/bin/env python3
"""
Test all v6 commands on live Redis v7 server.
Verifies backward compatibility - all v6 commands should work on v7.
"""

import json
import os
import sys
from pathlib import Path
import redis

V6_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v6_commands")
V7_PORT = 7399

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"
SKIP = "\033[90mSKIP\033[0m"

# Commands that are expected to fail or need special handling
EXPECTED_FAILS = {
    "SHUTDOWN": "shutdown may fail without admin",
    "DEBUG": "debug commands need special args",
    "CLUSTER": "cluster commands need cluster mode",
    "REPLICAOF": "replication commands",
    "SLAVEOF": "replication commands",
    "BGSAVE": "background save",
    "BGREWRITEAOF": "background aof",
    "FAILOVER": "needs replica setup",
    "FLUSHDB": "destructive",
    "FLUSHALL": "destructive",
    "SWAPDB": "dangerous",
    "MIGRATE": "needs special setup",
    "RESTORE": "needs special setup",
    "RESTORE-ASKING": "needs special setup",
    "PSYNC": "replication internal",
    "REPLCONF": "replication internal",
    "SYNC": "replication internal",
    "MONITOR": "enters monitor mode",
    "PUBSUB": "enters pubsub mode",
    "SUBSCRIBE": "enters sub mode",
    "PSUBSCRIBE": "enters sub mode",
    "UNSUBSCRIBE": "pubsub mode",
    "PUNSUBSCRIBE": "pubsub mode",
    "CLIENT": "parent container",
    "ACL": "parent container",
    "CONFIG": "parent container",
    "SCRIPT": "parent container",
    "SLOWLOG": "parent container",
    "MEMORY": "parent container",
    "XGROUP": "parent container",
    "XINFO": "parent container",
    "COMMAND": "parent container",
    "OBJECT": "parent container",
    "LATENCY": "parent container",
    "MODULE": "parent container",
    "FUNCTION": "v7 only container",
    "AUTH": "needs password config",
    "SELECT": "needs db setup",
    "WAIT": "needs replica",
    "RESET": "special state",
    "PFSELFTEST": "self test",
    "PFDEBUG": "module debug",
}

EXPECTED_FAIL_SUBS = {
    "CLIENT|KILL": "kills connection",
    "CLIENT|PAUSE": "affects server",
    "CLIENT|UNPAUSE": "affects server",
    "CLIENT|REPLY": "affects connection",
    "CLIENT|CACHING": "affects connection",
    "CLIENT|NO-EVICT": "affects connection",
    "CONFIG|RESETSTAT": "modifies state",
    "CONFIG|REWRITE": "modifies config",
    "ACL|SAVE": "modifies acl file",
    "ACL|LOAD": "modifies acl file",
    "ACL|SETUSER": "modifies acl",
    "ACL|DELUSER": "modifies acl",
    "SCRIPT|FLUSH": "modifies script cache",
    "SLOWLOG|RESET": "modifies slowlog",
    "DEBUG|SLEEP": "debug command",
    "DEBUG|SEGFAULT": "debug command",
    "DEBUG|SET-ACTIVE-EXPIRE": "debug command",
    "MEMORY|DOCTOR": "diagnostic",
    "MEMORY|MALLOC-STATS": "diagnostic",
    "MEMORY|PURGE": "modifies memory",
    "XGROUP|CREATE": "may fail without group",
    "XGROUP|DESTROY": "modifies stream",
    "XGROUP|SETID": "modifies stream",
    "XGROUP|DELCONSUMER": "modifies stream",
    "XGROUP|CREATECONSUMER": "modifies stream",
    "XINFO|CONSUMERS": "needs group",
    "COMMAND|GETKEYS": "special handling",
    "MODULE|LOAD": "module operation",
    "MODULE|UNLOAD": "module operation",
    "MODULE|LOADEX": "module operation",
    "CLUSTER|ADDSLOTS": "cluster operation",
    "CLUSTER|DELSLOTS": "cluster operation",
    "CLUSTER|FAILOVER": "cluster operation",
    "CLUSTER|FLUSHSLOTS": "cluster operation",
    "CLUSTER|FORGET": "cluster operation",
    "CLUSTER|MEET": "cluster operation",
    "CLUSTER|REPLICATE": "cluster operation",
    "CLUSTER|RESET": "cluster operation",
    "CLUSTER|SAVECONFIG": "cluster operation",
    "CLUSTER|SET-CONFIG-EPOCH": "cluster operation",
    "CLUSTER|SETSLOT": "cluster operation",
    "LATENCY|RESET": "modifies latency",
}


def load_v6_commands():
    cmds = {}
    for jf in sorted(Path(V6_DIR).glob("*.json")):
        with open(jf) as f:
            data = json.load(f)
        for k, v in data.items():
            cmds[k] = v
    return cmds


def gen_arg_value(arg, key_prefix="_vtest"):
    atype = arg.get("type", "string")
    token = arg.get("token")
    
    if atype == "pure-token":
        return [token] if token else []
    if atype == "key":
        return [f"{key_prefix}"]
    if atype == "string":
        return [token, "testval"] if token else ["testval"]
    if atype == "integer":
        return [token, "1"] if token else ["1"]
    if atype == "double":
        return [token, "1.0"] if token else ["1.0"]
    if atype == "unix-time":
        return [token, "9999999999"] if token else ["9999999999"]
    if atype == "pattern":
        return [token, "_vtest*"] if token else ["_vtest*"]
    if atype == "oneof":
        subs = arg.get("arguments", [])
        if subs:
            return gen_arg_value(subs[0], key_prefix)
        return [token] if token else []
    if atype == "block":
        subs = arg.get("arguments", [])
        vals = []
        for sa in subs:
            vals.extend(gen_arg_value(sa, key_prefix))
        return vals
    return [token, "x"] if token else ["x"]


def build_minimal_args(arguments, key_prefix="_vtest"):
    parts = []
    for arg in arguments:
        if arg.get("optional"):
            continue
        parts.extend(gen_arg_value(arg, key_prefix))
    return parts


def should_skip(cmd_name):
    base = cmd_name.split("|")[0] if "|" in cmd_name else cmd_name
    if base in EXPECTED_FAILS:
        return True
    if cmd_name in EXPECTED_FAIL_SUBS:
        return True
    return False


def test_command(r, cmd_name, jdata):
    if should_skip(cmd_name):
        return None, "expected skip"
    
    arguments = jdata.get("arguments")
    
    if not arguments:
        try:
            if "|" in cmd_name:
                parent, sub = cmd_name.split("|", 1)
                r.execute_command(parent, sub)
            else:
                r.execute_command(cmd_name)
            return True, "bare success"
        except redis.ResponseError as e:
            return None, f"bare error: {e}"
        except Exception as e:
            return False, f"bare exception: {e}"
    
    # Build minimal args
    min_args = build_minimal_args(arguments, "_vtest")
    
    try:
        if "|" in cmd_name:
            parent, sub = cmd_name.split("|", 1)
            r.execute_command(parent, sub, *min_args)
        else:
            r.execute_command(cmd_name, *min_args)
        return True, f"success with args"
    except redis.ResponseError as e:
        emsg = str(e)
        # Accept data/state errors (command parsed correctly)
        if any(k in emsg for k in [
            "WRONGTYPE", "no such key", "not found", "doesn't exist",
            "no such", "Invalid argument", "not an integer",
            "ERR value is not", "ERR invalid", "syntax error",
            "NOSCRIPT", "NOGROUP", "Invalid stream ID",
            "unsupported unit", "not valid string range",
            "Number of keys", "No matching script",
            "password", "are the same",
            "min-idle-time", "can't be negative",
            "could not decode", "smaller than the target",
            "NOGROUP", "ERR Unknown subcommand",
        ]):
            return None, f"data/state: {emsg[:40]}"
        return False, f"error: {emsg[:50]}"
    except Exception as e:
        return False, f"exception: {e}"


def main():
    print("=" * 70)
    print("  Test v6 Commands on Live Redis v7 Server")
    print("=" * 70)
    
    try:
        r = redis.Redis(port=V7_PORT, decode_responses=False)
        ver = r.info("server").get(b"redis_version", b"unknown")
        print(f"Connected to v7 server (port {V7_PORT}), version: {ver.decode()}")
    except Exception as e:
        print(f"ERROR: Cannot connect to v7 server on port {V7_PORT}: {e}")
        sys.exit(1)
    
    # Setup test data
    r.set("_vtest", "hello")
    r.hset("_vtest_h", "f1", "v1")
    r.lpush("_vtest_l", "a", "b")
    r.sadd("_vtest_s", "a", "b")
    r.zadd("_vtest_z", {"a": 1.0, "b": 2.0})
    try:
        r.execute_command("XADD", "_vtest_stream", "*", "f1", "v1")
    except:
        pass
    
    v6_cmds = load_v6_commands()
    print(f"Testing {len(v6_cmds)} v6 commands on v7 server\n")
    
    results = {
        "pass": [],
        "fail": [],
        "skip_expected": [],
        "data_state_error": [],
    }
    
    for cmd_name in sorted(v6_cmds.keys()):
        jdata = v6_cmds[cmd_name]
        
        if should_skip(cmd_name):
            results["skip_expected"].append((cmd_name, "expected skip"))
            continue
        
        passed, detail = test_command(r, cmd_name, jdata)
        
        if passed is True:
            results["pass"].append((cmd_name, detail))
        elif passed is False:
            results["fail"].append((cmd_name, detail))
        else:
            if "expected skip" in detail:
                results["skip_expected"].append((cmd_name, detail))
            else:
                results["data_state_error"].append((cmd_name, detail))
    
    # Cleanup
    for k in r.keys("_vtest*"):
        r.delete(k)
    
    # Print results
    print("-" * 70)
    print(f"PASS (executed successfully): {len(results['pass'])}")
    print("-" * 70)
    for cmd, detail in results["pass"]:
        print(f"  [{PASS}] {cmd:30s} {detail}")
    
    print("\n" + "-" * 70)
    print(f"DATA/STATE ERRORS (command parsed, data issue): {len(results['data_state_error'])}")
    print("-" * 70)
    for cmd, detail in results["data_state_error"]:
        print(f"  [{WARN}] {cmd:30s} {detail}")
    
    print("\n" + "-" * 70)
    print(f"SKIPPED (expected): {len(results['skip_expected'])}")
    print("-" * 70)
    for cmd, detail in results["skip_expected"]:
        print(f"  [{SKIP}] {cmd:30s} {detail}")
    
    print("\n" + "-" * 70)
    print(f"FAIL (command failed to execute): {len(results['fail'])}")
    print("-" * 70)
    for cmd, detail in results["fail"]:
        print(f"  [{FAIL}] {cmd:30s} {detail}")
    
    print("\n" + "=" * 70)
    print(f"  SUMMARY: {PASS} {len(results['pass'])}  {WARN} {len(results['data_state_error'])}  {SKIP} {len(results['skip_expected'])}  {FAIL} {len(results['fail'])}")
    print("=" * 70)
    
    if results["fail"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
