#!/usr/bin/env python3
"""
Load v6 command meta JSON, execute with full args on Redis v7 server.
Get results and summarize.
"""

import json
import os
import sys
from pathlib import Path
import redis
import random
import string

V6_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v6_commands")
V7_PORT = 7399

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"

SKIP_CONTAINERS = {
    "ACL", "CLIENT", "CLUSTER", "COMMAND", "CONFIG", "DEBUG", "FUNCTION",
    "LATENCY", "MEMORY", "MODULE", "OBJECT", "PUBSUB", "SCRIPT", "SLOWLOG",
    "XGROUP", "XINFO",
}

SKIP_EXEC = {
    "SHUTDOWN", "BGSAVE", "BGREWRITEAOF", "FAILOVER", "FLUSHDB", "FLUSHALL",
    "SWAPDB", "MIGRATE", "RESTORE", "RESTORE-ASKING", "PSYNC", "REPLCONF",
    "SYNC", "REPLICAOF", "SLAVEOF", "MONITOR", "SELECT", "RESET",
    "PFSELFTEST", "PFDEBUG", "AUTH",
    "SUBSCRIBE", "PSUBSCRIBE", "UNSUBSCRIBE", "PUNSUBSCRIBE",
    "BLPOP", "BRPOP", "BRPOPLPUSH", "BLMOVE", "BZPOPMIN", "BZPOPMAX",
    "XREAD", "XREADGROUP",
    "HOST:", "POST",
}

SKIP_SUBS = {
    "ACL|SAVE", "ACL|LOAD", "ACL|SETUSER", "ACL|DELUSER", "ACL|USERS",
    "CLIENT|KILL", "CLIENT|PAUSE", "CLIENT|UNPAUSE", "CLIENT|REPLY",
    "CLIENT|CACHING", "CLIENT|NO-EVICT", "CLIENT|TRACKING", "CLIENT|TRACKINGINFO",
    "CONFIG|RESETSTAT", "CONFIG|REWRITE",
    "SCRIPT|FLUSH", "SCRIPT|KILL",
    "SLOWLOG|RESET",
    "MEMORY|DOCTOR", "MEMORY|MALLOC-STATS", "MEMORY|PURGE",
    "DEBUG|SLEEP", "DEBUG|SEGFAULT", "DEBUG|SET-ACTIVE-EXPIRE",
    "MODULE|LOAD", "MODULE|UNLOAD", "MODULE|LOADEX",
    "CLUSTER|ADDSLOTS", "CLUSTER|DELSLOTS", "CLUSTER|FAILOVER",
    "CLUSTER|FLUSHSLOTS", "CLUSTER|FORGET", "CLUSTER|MEET",
    "CLUSTER|REPLICATE", "CLUSTER|RESET", "CLUSTER|SAVECONFIG",
    "CLUSTER|SET-CONFIG-EPOCH", "CLUSTER|SETSLOT",
    "LATENCY|RESET",
    "XGROUP|CREATE", "XGROUP|DESTROY", "XGROUP|SETID",
    "XGROUP|DELCONSUMER", "XGROUP|CREATECONSUMER",
}


def load_v6_commands():
    cmds = {}
    for jf in sorted(Path(V6_DIR).glob("*.json")):
        with open(jf) as f:
            data = json.load(f)
        for k, v in data.items():
            cmds[k] = v
    return cmds


def random_key(prefix="test"):
    return f"{prefix}_{random.randint(1000,9999)}"


def gen_full_args(arguments, key_prefix="test", depth=0):
    if depth > 10:
        return []
    
    parts = []
    for arg in arguments:
        name = arg.get("name", "")
        atype = arg.get("type", "string")
        token = arg.get("token")
        optional = arg.get("optional", False)
        multiple = arg.get("multiple", False)
        multiple_token = arg.get("multiple_token")
        
        nested = arg.get("arguments", [])
        
        if atype == "pure-token":
            if token:
                parts.append(token)
        
        elif atype == "key":
            key = random_key(key_prefix)
            if multiple:
                parts.extend([key, random_key(key_prefix)])
            else:
                parts.append(key)
        
        elif atype == "string":
            val = f"value_{random.randint(1,100)}"
            if token:
                parts.extend([token, val])
            else:
                parts.append(val)
        
        elif atype == "integer":
            val = str(random.randint(1, 100))
            if token:
                parts.extend([token, val])
            else:
                parts.append(val)
        
        elif atype == "double":
            val = str(random.random() * 10)
            if token:
                parts.extend([token, val])
            else:
                parts.append(val)
        
        elif atype == "unix-time":
            val = str(random.randint(1000000000, 9999999999))
            if token:
                parts.extend([token, val])
            else:
                parts.append(val)
        
        elif atype == "pattern":
            val = "*"
            if token:
                parts.extend([token, val])
            else:
                parts.append(val)
        
        elif atype == "oneof":
            subs = arg.get("arguments", [])
            if subs:
                sub_args = gen_full_args([subs[0]], key_prefix, depth+1)
                parts.extend(sub_args)
        
        elif atype == "block":
            if nested:
                block_args = gen_full_args(nested, key_prefix, depth+1)
                if token:
                    parts.append(token)
                parts.extend(block_args)
    
    return parts


def should_skip(cmd_name):
    base = cmd_name.split("|")[0] if "|" in cmd_name else cmd_name
    
    if base in SKIP_CONTAINERS:
        return f"container command"
    if cmd_name in SKIP_EXEC:
        return f"dangerous/special command"
    if cmd_name in SKIP_SUBS:
        return f"dangerous subcommand"
    if base in SKIP_EXEC:
        return f"in skip list"
    return None


def execute_cmd(r, cmd_name, jdata):
    skip_reason = should_skip(cmd_name)
    if skip_reason:
        return "skip", skip_reason, None
    
    arguments = jdata.get("arguments", [])
    
    if not arguments:
        try:
            if "|" in cmd_name:
                parent, sub = cmd_name.split("|", 1)
                result = r.execute_command(parent, sub)
            else:
                result = r.execute_command(cmd_name)
            return "success", "bare command", type(result).__name__
        except redis.ResponseError as e:
            return "error", str(e)[:60], None
        except Exception as e:
            return "error", f"exception: {e}", None
    
    full_args = gen_full_args(arguments, f"test_{cmd_name.lower()}")
    
    if not full_args:
        try:
            if "|" in cmd_name:
                parent, sub = cmd_name.split("|", 1)
                result = r.execute_command(parent, sub)
            else:
                result = r.execute_command(cmd_name)
            return "success", "no args needed", type(result).__name__
        except redis.ResponseError as e:
            return "error", str(e)[:60], None
        except Exception as e:
            return "error", f"exception: {e}", None
    
    try:
        if "|" in cmd_name:
            parent, sub = cmd_name.split("|", 1)
            result = r.execute_command(parent, sub, *full_args)
        else:
            result = r.execute_command(cmd_name, *full_args)
        return "success", f"args: {len(full_args)}", type(result).__name__
    except redis.ResponseError as e:
        emsg = str(e)
        if any(k in emsg.lower() for k in [
            "wrong number", "wrong number of arguments",
            "not enough arguments", "too many arguments",
            "syntax error",
        ]):
            return "arg_error", emsg[:60], None
        if any(k in emsg for k in [
            "WRONGTYPE", "no such key", "not found", "doesn't exist",
            "NOGROUP", "NOSCRIPT", "Invalid", "not an integer",
            "value is not", "out of range", "not valid",
            "ERR", "could not",
        ]):
            return "data_error", emsg[:60], None
        return "error", emsg[:60], None
    except Exception as e:
        return "error", f"exception: {e}", None


def main():
    print("=" * 70)
    print("  Execute v6 Commands with Full Args on Redis v7")
    print("=" * 70)
    
    try:
        r = redis.Redis(port=V7_PORT, decode_responses=False)
        ver = r.info("server").get(b"redis_version", b"unknown")
        print(f"Connected to v7 server (port {V7_PORT}), version: {ver.decode()}")
    except Exception as e:
        print(f"ERROR: Cannot connect to v7 server on port {V7_PORT}: {e}")
        sys.exit(1)
    
    v6_cmds = load_v6_commands()
    print(f"Loaded {len(v6_cmds)} v6 commands\n")
    
    results = {
        "success": [],
        "data_error": [],
        "arg_error": [],
        "error": [],
        "skip": [],
    }
    
    for cmd_name in sorted(v6_cmds.keys()):
        jdata = v6_cmds[cmd_name]
        status, detail, result_type = execute_cmd(r, cmd_name, jdata)
        results[status].append((cmd_name, detail, result_type))
    
    print("=" * 70)
    print("  RESULTS SUMMARY")
    print("=" * 70)
    
    print(f"\n[{PASS}] SUCCESS ({len(results['success'])} commands):")
    for cmd, detail, rtype in sorted(results["success"])[:20]:
        print(f"  {cmd:35s} {detail:30s} -> {rtype}")
    if len(results["success"]) > 20:
        print(f"  ... and {len(results['success']) - 20} more")
    
    print(f"\n[{WARN}] DATA/STATE ERRORS ({len(results['data_error'])} commands):")
    print("  (command syntax correct, data issue - expected)")
    for cmd, detail, rtype in sorted(results["data_error"])[:10]:
        print(f"  {cmd:35s} {detail}")
    if len(results["data_error"]) > 10:
        print(f"  ... and {len(results['data_error']) - 10} more")
    
    print(f"\n[ARG_ERROR] ARGUMENT ERRORS ({len(results['arg_error'])} commands):")
    print("  (command syntax issue - may need fix)")
    for cmd, detail, rtype in sorted(results["arg_error"]):
        print(f"  {cmd:35s} {detail}")
    
    print(f"\n[{FAIL}] ERRORS ({len(results['error'])} commands):")
    for cmd, detail, rtype in sorted(results["error"]):
        print(f"  {cmd:35s} {detail}")
    
    print(f"\n[SKIP] SKIPPED ({len(results['skip'])} commands):")
    skip_counts = {}
    for cmd, detail, rtype in results["skip"]:
        skip_counts[detail] = skip_counts.get(detail, 0) + 1
    for reason, count in sorted(skip_counts.items(), key=lambda x: -x[1]):
        print(f"  {count:3d} - {reason}")
    
    print("\n" + "=" * 70)
    total_executed = len(results["success"]) + len(results["data_error"]) + len(results["arg_error"]) + len(results["error"])
    print(f"  Total: {len(v6_cmds)} commands")
    print(f"  Executed: {total_executed}")
    print(f"  Skipped: {len(results['skip'])}")
    print(f"  Success: {len(results['success'])}")
    print(f"  Data errors: {len(results['data_error'])} (expected)")
    print(f"  Arg errors: {len(results['arg_error'])}")
    print(f"  Other errors: {len(results['error'])}")
    print("=" * 70)


if __name__ == "__main__":
    main()
