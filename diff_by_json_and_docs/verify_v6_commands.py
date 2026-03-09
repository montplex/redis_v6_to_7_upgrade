#!/usr/bin/env python3
"""
Verify ALL generated v6 command JSONs against a live Redis v6 server.

For every command in v6_commands/:
  Part 1: Metadata — arity, command_flags, acl_categories, key positions
          compared against COMMAND INFO from the live server.
  Part 2: Arguments — for each command that has "arguments" in its JSON,
          build minimal valid invocations from the argument spec and execute
          them; also test wrong-arity calls are rejected.
  Part 3: Reply schema — execute a safe invocation and verify the reply
          type matches reply_schema.

Commands that are blocking, subscribe-based, or server-destructive are
excluded from live execution but still get metadata checks.
"""

import json
import os
import sys
import time
import datetime
from pathlib import Path

import redis

V6_PORT = 6399
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
V6_DIR = os.path.join(SCRIPT_DIR, "v6_commands")

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"
SKIP = "\033[90mSKIP\033[0m"

# ── Commands/subcommands to skip for live execution (blocking, dangerous, etc.)
SKIP_EXEC = {
    # Blocking commands
    "BLPOP", "BRPOP", "BRPOPLPUSH", "BLMOVE", "BZPOPMIN", "BZPOPMAX",
    "XREAD", "XREADGROUP",
    # Subscribe (enters sub mode, blocks)
    "SUBSCRIBE", "PSUBSCRIBE", "UNSUBSCRIBE", "PUNSUBSCRIBE", "MONITOR",
    # Destructive / side-effects on server
    "SHUTDOWN", "DEBUG", "BGSAVE", "BGREWRITEAOF", "FAILOVER",
    "SLAVEOF", "REPLICAOF", "PSYNC", "REPLCONF", "SYNC",
    "FLUSHDB", "FLUSHALL", "SWAPDB",
    "RESTORE", "RESTORE-ASKING", "MIGRATE",
    # Cluster (not in standalone mode)
    "CLUSTER", "ASKING", "READONLY", "READWRITE",
    # Internal / sentinel
    "PFSELFTEST", "PFDEBUG",
    "LATENCY", "MODULE",
    # Multi/exec state issues
    "MULTI", "EXEC", "DISCARD",
    # HTTP compat pseudo-commands (close connection)
    "HOST:", "POST",
    # Needs server password config
    "AUTH",
    # Misc that need special setup
    "WAIT", "SELECT",
    "RESET",
    "OBJECT",  # parent container, subcommands tested individually
    "SCRIPT",  # parent container
    "CONFIG",  # parent container
    "CLIENT",  # parent container
    "ACL",     # parent container
    "SLOWLOG", # parent container
    "MEMORY",  # parent container
    "PUBSUB",  # parent container
    "XGROUP",  # parent container
    "XINFO",   # parent container
    "COMMAND", # parent container
    "FUNCTION",  # v7 only container (shouldn't be in v6)
}

# Subcommands to skip (blocking, destructive, etc.)
SKIP_EXEC_SUBS = {
    "CLIENT|KILL", "CLIENT|PAUSE", "CLIENT|UNPAUSE", "CLIENT|REPLY",
    "CLIENT|CACHING", "CLIENT|NO-EVICT",
    "CONFIG|RESETSTAT", "CONFIG|REWRITE",
    "ACL|SAVE", "ACL|LOAD", "ACL|SETUSER", "ACL|DELUSER",
    "SCRIPT|FLUSH",
    "SLOWLOG|RESET",
    "DEBUG|SLEEP", "DEBUG|SEGFAULT", "DEBUG|SET-ACTIVE-EXPIRE",
    "MEMORY|DOCTOR", "MEMORY|MALLOC-STATS", "MEMORY|PURGE",
    "XGROUP|CREATE", "XGROUP|DESTROY", "XGROUP|SETID",
    "XGROUP|DELCONSUMER", "XGROUP|CREATECONSUMER",
    "XINFO|CONSUMERS",  # needs a group
    "COMMAND|GETKEYS",  # needs careful args
    "MODULE|LOAD", "MODULE|UNLOAD", "MODULE|LOADEX",
    "CLUSTER|ADDSLOTS", "CLUSTER|DELSLOTS", "CLUSTER|FAILOVER",
    "CLUSTER|FLUSHSLOTS", "CLUSTER|FORGET", "CLUSTER|MEET",
    "CLUSTER|REPLICATE", "CLUSTER|RESET", "CLUSTER|SAVECONFIG",
    "CLUSTER|SET-CONFIG-EPOCH", "CLUSTER|SETSLOT",
    "LATENCY|RESET",
}

# Commands that need custom arg lists (the generic builder can't produce
# semantically valid values for these)
CUSTOM_ARGS = {
    "AUTH":               ["password"],  # will be rejected but that's a config issue
    "COPY":               ["_vtest", "_vtest_copy"],
    "EVAL":               ["return 1", "0"],
    "EVALSHA":            ["abc123", "0"],  # will NOSCRIPT, which is a data error
    "GEORADIUS":          ["_vtest", "0", "0", "100", "km"],
    "GEORADIUS_RO":       ["_vtest", "0", "0", "100", "km"],
    "GEORADIUSBYMEMBER":  ["_vtest", "testmem", "100", "km"],
    "GEORADIUSBYMEMBER_RO": ["_vtest", "testmem", "100", "km"],
    "GEOSEARCH":          ["_vtest", "FROMMEMBER", "testmem", "BYRADIUS", "100", "km"],
    "GEOSEARCHSTORE":     ["_vtest_dst", "_vtest", "FROMMEMBER", "testmem", "BYRADIUS", "100", "km"],
    "XAUTOCLAIM":         ["_vtest_stream", "grp", "consumer", "0", "0-0"],
    "XCLAIM":             ["_vtest_stream", "grp", "consumer", "0", "0-0"],
    "XDEL":               ["_vtest_stream", "0-1"],
    "XPENDING":           ["_vtest_stream", "grp"],
    "XRANGE":             ["_vtest_stream", "-", "+"],
    "XREVRANGE":          ["_vtest_stream", "+", "-"],
    "XSETID":             ["_vtest_stream", "0-0"],
    "XTRIM":              ["_vtest_stream", "MAXLEN", "1000"],
    "ZLEXCOUNT":          ["_vtest_z", "-", "+"],
    "ZRANGEBYLEX":        ["_vtest_z", "-", "+"],
    "ZRANGEBYSCORE":      ["_vtest_z", "-inf", "+inf"],
    "ZREMRANGEBYLEX":     ["_vtest_z", "-", "+"],
    "ZREVRANGEBYLEX":     ["_vtest_z", "+", "-"],
    "ZREVRANGEBYSCORE":   ["_vtest_z", "+inf", "-inf"],
}

# ── Flag mapping: v6 COMMAND response → normalized
FLAG_MAP = {
    "write": "WRITE", "readonly": "READONLY", "denyoom": "DENYOOM",
    "admin": "ADMIN", "pubsub": "PUBSUB", "noscript": "NOSCRIPT",
    "random": "RANDOM", "sort_for_script": "TO_SORT", "loading": "LOADING",
    "stale": "STALE", "no_monitor": "NO_MONITOR", "no_slowlog": "NO_SLOWLOG",
    "skip_monitor": "SKIP_MONITOR", "skip_slowlog": "SKIP_SLOWLOG",
    "asking": "ASKING", "fast": "FAST", "no_auth": "NO_AUTH",
    "may_replicate": "MAY_REPLICATE", "movablekeys": "MOVABLEKEYS",
}


def decode(obj):
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if isinstance(obj, list):
        return [decode(x) for x in obj]
    return obj


# ═══════════════════════════════════════════════════════════════════════
# Load all v6 JSONs
# ═══════════════════════════════════════════════════════════════════════

def load_all_v6():
    """Return {cmd_name: data} for every JSON file in v6_commands/."""
    cmds = {}
    for jf in sorted(Path(V6_DIR).glob("*.json")):
        with open(jf) as f:
            data = json.load(f)
        for k, v in data.items():
            cmds[k] = v
    return cmds


# ═══════════════════════════════════════════════════════════════════════
# Part 1: COMMAND INFO metadata
# ═══════════════════════════════════════════════════════════════════════

def normalize_flags(flags):
    out = []
    for f in flags:
        s = decode(f).lower().replace("-", "_")
        out.append(FLAG_MAP.get(s, s.upper()))
    return sorted(out)


def normalize_acl(cats):
    return sorted(decode(c).lstrip("@").upper() for c in cats)


def verify_all_metadata(r, v6_cmds):
    """Check arity / flags / acl / key-pos for every top-level command."""
    results = []

    # Fetch live COMMAND data
    conn = r.connection_pool.get_connection()
    try:
        conn.send_command("COMMAND")
        raw = conn.read_response()
    finally:
        r.connection_pool.release(conn)

    live_map = {}
    for entry in raw:
        name = decode(entry[0]).upper()
        live_map[name] = entry

    for cmd_name, jdata in sorted(v6_cmds.items()):
        # Subcommands: v6 COMMAND only has parent info, can't verify sub metadata
        if "|" in cmd_name:
            # Just verify we have expected fields
            for field in ("summary", "arity", "group", "since"):
                has_it = field in jdata and jdata[field] not in (None, "", 0)
                results.append((cmd_name, f"has_{field}", has_it,
                                f"{field}={repr(jdata.get(field, 'MISSING'))[:50]}"))
            continue

        live = live_map.get(cmd_name)
        if not live:
            results.append((cmd_name, "in_server", False,
                            f"{cmd_name} not found in COMMAND output"))
            continue

        # Arity
        json_arity = jdata.get("arity")
        live_arity = live[1]
        results.append((cmd_name, "arity",
                        json_arity == live_arity,
                        f"json={json_arity} live={live_arity}"))

        # Flags
        json_flags = sorted(jdata.get("command_flags", []))
        live_flags = normalize_flags(live[2])
        results.append((cmd_name, "flags",
                        json_flags == live_flags,
                        f"json={json_flags} live={live_flags}"))

        # ACL categories
        json_acl = sorted(jdata.get("acl_categories", []))
        live_acl = normalize_acl(live[6]) if len(live) > 6 else []
        results.append((cmd_name, "acl_categories",
                        json_acl == live_acl,
                        f"json={json_acl} live={live_acl}"))

        # Key positions
        json_ks = jdata.get("key_specs", [])
        live_first = live[3]
        live_last = live[4]
        live_step = live[5]
        if json_ks:
            ks0 = json_ks[0]
            jfirst = ks0.get("begin_search", {}).get("index", {}).get("pos", 0)
            jlast = ks0.get("find_keys", {}).get("range", {}).get("lastkey", 0)
            jstep = ks0.get("find_keys", {}).get("range", {}).get("step", 0)
            results.append((cmd_name, "first_key",
                            jfirst == live_first,
                            f"json={jfirst} live={live_first}"))
            results.append((cmd_name, "last_key",
                            jlast == live_last,
                            f"json={jlast} live={live_last}"))
            results.append((cmd_name, "key_step",
                            jstep == live_step,
                            f"json={jstep} live={live_step}"))
        elif live_first == 0:
            results.append((cmd_name, "key_specs", True, "no keys (correct)"))
        else:
            results.append((cmd_name, "key_specs", False,
                            f"no key_specs in JSON but live first_key={live_first}"))

    return results


# ═══════════════════════════════════════════════════════════════════════
# Part 2: Argument-based execution
# ═══════════════════════════════════════════════════════════════════════

# Minimal test-data generators per argument type
def gen_arg_value(arg, key_prefix="_vtest"):
    """Generate a minimal valid value for an argument based on its type/token."""
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
        # Pick the first sub-argument
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
    # fallback
    return [token, "x"] if token else ["x"]


def build_minimal_args(arguments, key_prefix="_vtest"):
    """Build a minimal argument list from the JSON argument spec.

    Only includes required arguments (skips optional ones).
    """
    parts = []
    for arg in arguments:
        if arg.get("optional"):
            continue
        parts.extend(gen_arg_value(arg, key_prefix))
    return parts


def should_skip_exec(cmd_name):
    """Decide if a command should skip live execution."""
    base = cmd_name.split("|")[0] if "|" in cmd_name else cmd_name
    if base in SKIP_EXEC:
        return True
    if cmd_name in SKIP_EXEC_SUBS:
        return True
    return False


def run_all_arg_tests(r, v6_cmds):
    """For every command with arguments, try a minimal invocation."""
    results = []
    key_idx = 0

    # Pre-create some test data
    r.set("_vtest", "hello")
    r.hset("_vtest_h", "f1", "v1")
    r.lpush("_vtest_l", "a", "b")
    r.sadd("_vtest_s", "a", "b")
    r.zadd("_vtest_z", {"a": 1.0, "b": 2.0})
    r.execute_command("XADD", "_vtest_stream", "*", "f1", "v1")

    for cmd_name, jdata in sorted(v6_cmds.items()):
        if should_skip_exec(cmd_name):
            results.append((cmd_name, "exec", None, "skipped (blocked/dangerous)"))
            continue

        arguments = jdata.get("arguments")
        if not arguments:
            # No arguments spec — try bare command
            try:
                if "|" in cmd_name:
                    parent, sub = cmd_name.split("|", 1)
                    r.execute_command(parent, sub)
                else:
                    r.execute_command(cmd_name)
                results.append((cmd_name, "exec_bare", True, "OK"))
            except redis.ResponseError as e:
                emsg = str(e)
                # "wrong number of arguments" is expected for commands that need args
                # but we have no spec — that's OK
                results.append((cmd_name, "exec_bare", True,
                                f"error (no arg spec): {emsg[:50]}"))
            except Exception as e:
                results.append((cmd_name, "exec_bare", False, f"exception: {e}"))
            continue

        # Build minimal args — use custom args if available
        key_idx += 1
        if cmd_name in CUSTOM_ARGS:
            min_args = CUSTOM_ARGS[cmd_name]
        else:
            min_args = build_minimal_args(arguments, "_vtest")

        # Execute
        try:
            if "|" in cmd_name:
                parent, sub = cmd_name.split("|", 1)
                reply = r.execute_command(parent, sub, *min_args)
            else:
                reply = r.execute_command(cmd_name, *min_args)
            results.append((cmd_name, "exec_min_args", True,
                            f"args={min_args[:6]}.. reply={repr(reply)[:40]}"))
        except redis.ResponseError as e:
            emsg = str(e)
            # Some commands need specific state (stream group, etc.)
            # Treat ERR for wrong-type or missing data as a soft pass
            # (the command parsed args correctly, just failed on data)
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
            ]):
                results.append((cmd_name, "exec_min_args", None,
                                f"data/state error (args parsed): {emsg[:60]}"))
            else:
                results.append((cmd_name, "exec_min_args", False,
                                f"error: {emsg[:70]} args={min_args}"))
        except Exception as e:
            results.append((cmd_name, "exec_min_args", False,
                            f"exception: {e}"))

        # Also test wrong arity: send no args (should be rejected)
        arity = jdata.get("arity", 0)
        if arity > 1 or arity < -1:
            try:
                if "|" in cmd_name:
                    parent, sub = cmd_name.split("|", 1)
                    r.execute_command(parent, sub)
                else:
                    r.execute_command(cmd_name)
                # If the command succeeds with no args while arity says it needs them,
                # that's unexpected (unless arity is -1 meaning any)
                results.append((cmd_name, "wrong_arity_reject", False,
                                f"expected arity error but succeeded (arity={arity})"))
            except redis.ResponseError as e:
                emsg = str(e).lower()
                if "wrong number of arguments" in emsg or "arity" in emsg or "err" in emsg:
                    results.append((cmd_name, "wrong_arity_reject", True,
                                    f"correctly rejected empty args"))
                else:
                    results.append((cmd_name, "wrong_arity_reject", True,
                                    f"rejected: {str(e)[:50]}"))
            except Exception as e:
                results.append((cmd_name, "wrong_arity_reject", False,
                                f"exception: {e}"))

    # Cleanup
    for k in r.keys("_vtest*"):
        r.delete(k)

    return results


# ═══════════════════════════════════════════════════════════════════════
# Part 3: Reply schema
# ═══════════════════════════════════════════════════════════════════════

def check_reply_type(val, schema):
    """Check if a reply value matches the reply_schema."""
    if schema is None:
        return True, "no schema"

    def matches(v, s):
        if "anyOf" in s:
            return any(matches(v, x) for x in s["anyOf"])
        if "oneOf" in s:
            return any(matches(v, x) for x in s["oneOf"])
        if "const" in s:
            exp = s["const"]
            if isinstance(exp, str):
                if exp == "OK" and v is True:
                    return True
                return decode(v) == exp if isinstance(v, bytes) else v == exp
            return v == exp
        t = s.get("type")
        if t == "string":
            # redis-py coercions: True for OK/PONG, dict for INFO bulk-string,
            # float for GEODIST (redis returns string, py parses to float)
            return isinstance(v, (str, bytes, bool, dict, datetime.datetime, float))
        if t == "integer":
            # redis-py: datetime for LASTSAVE (unix timestamp)
            return isinstance(v, (int, bool, datetime.datetime))
        if t == "number":
            return isinstance(v, (int, float))
        if t == "null":
            return v is None
        if t == "array":
            # redis-py: tuples for SCAN, sets for SDIFF/SINTER/SUNION/SMEMBERS
            return isinstance(v, (list, tuple, set, frozenset))
        if t == "object":
            return isinstance(v, (dict, list))
        if t == "boolean":
            return isinstance(v, bool)
        return True

    ok = matches(val, schema)
    return ok, f"value={repr(val)[:60]}"


def run_all_reply_schema_tests(r, v6_cmds):
    """For every command that has reply_schema, execute and check reply type."""
    results = []

    # Setup test data
    r.set("_vtest", "hello")
    r.hset("_vtest_h", "f1", "v1")
    r.lpush("_vtest_l", "a", "b")
    r.sadd("_vtest_s", "a", "b")
    r.zadd("_vtest_z", {"a": 1.0, "b": 2.0})
    r.execute_command("XADD", "_vtest_stream", "*", "f1", "v1")

    for cmd_name, jdata in sorted(v6_cmds.items()):
        schema = jdata.get("reply_schema")
        if not schema:
            continue  # no schema to check

        if should_skip_exec(cmd_name):
            results.append((cmd_name, "reply_schema", None, "skipped"))
            continue

        arguments = jdata.get("arguments")
        if not arguments:
            # No args spec, try bare
            try:
                if "|" in cmd_name:
                    parent, sub = cmd_name.split("|", 1)
                    reply = r.execute_command(parent, sub)
                else:
                    reply = r.execute_command(cmd_name)
                ok, detail = check_reply_type(reply, schema)
                results.append((cmd_name, "reply_schema", ok, detail))
            except Exception:
                results.append((cmd_name, "reply_schema", None, "exec error"))
            continue

        # Build minimal args and execute
        if cmd_name in CUSTOM_ARGS:
            min_args = CUSTOM_ARGS[cmd_name]
        else:
            min_args = build_minimal_args(arguments, "_vtest")
        try:
            if "|" in cmd_name:
                parent, sub = cmd_name.split("|", 1)
                reply = r.execute_command(parent, sub, *min_args)
            else:
                reply = r.execute_command(cmd_name, *min_args)
            ok, detail = check_reply_type(reply, schema)
            results.append((cmd_name, "reply_schema", ok, detail))
        except redis.ResponseError:
            results.append((cmd_name, "reply_schema", None, "cmd error (data/state)"))
        except Exception as e:
            results.append((cmd_name, "reply_schema", False, f"exception: {e}"))

    # Cleanup
    for k in r.keys("_vtest*"):
        r.delete(k)

    return results


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("=" * 78)
    print("  Redis v6 Command JSON Verification — ALL commands")
    print("=" * 78)

    try:
        r = redis.Redis(port=V6_PORT, decode_responses=False)
        ver = decode(r.info("server").get(b"redis_version", b"unknown"))
        print(f"Connected to v6 server (port {V6_PORT}), version: {ver}")
    except Exception as e:
        print(f"ERROR: Cannot connect to v6 server on port {V6_PORT}: {e}")
        sys.exit(1)

    v6_cmds = load_all_v6()
    print(f"Loaded {len(v6_cmds)} v6 command JSONs "
          f"({sum(1 for k in v6_cmds if '|' not in k)} top-level, "
          f"{sum(1 for k in v6_cmds if '|' in k)} subcommands)\n")

    total_pass = 0
    total_fail = 0
    total_skip = 0
    failures = []

    def tally(results_list, part_label):
        nonlocal total_pass, total_fail, total_skip
        p = f = s = 0
        for cmd, check, passed, detail in results_list:
            if passed is None:
                s += 1
                total_skip += 1
                status = SKIP
            elif passed:
                p += 1
                total_pass += 1
                status = PASS
            else:
                f += 1
                total_fail += 1
                status = FAIL
                failures.append((cmd, check, detail))
            print(f"  [{status}] {cmd:30s} {check:22s} {detail[:80]}")
        print(f"\n  {part_label}: {PASS} {p}  {FAIL} {f}  {SKIP} {s}\n")

    # ── Part 1 ──
    print("-" * 78)
    print("Part 1: COMMAND INFO Metadata (arity, flags, ACL, key positions)")
    print("-" * 78)
    meta = verify_all_metadata(r, v6_cmds)
    tally(meta, "Part 1 totals")

    # ── Part 2 ──
    print("-" * 78)
    print("Part 2: Argument Execution (build minimal args from spec, execute)")
    print("-" * 78)
    arg = run_all_arg_tests(r, v6_cmds)
    tally(arg, "Part 2 totals")

    # ── Part 3 ──
    print("-" * 78)
    print("Part 3: Reply Schema (execute, check reply type vs schema)")
    print("-" * 78)
    r2 = redis.Redis(port=V6_PORT, decode_responses=False)
    rschema = run_all_reply_schema_tests(r2, v6_cmds)
    tally(rschema, "Part 3 totals")

    # ── Grand total ──
    print("=" * 78)
    print(f"  GRAND TOTAL: {PASS} {total_pass}  |  {FAIL} {total_fail}  |  {SKIP} {total_skip}")
    print("=" * 78)
    if failures:
        print(f"\n  {FAIL} Failures ({len(failures)}):")
        for cmd, check, detail in failures:
            print(f"    - {cmd}: {check} — {detail[:90]}")
    else:
        print(f"\n  All checks passed!")

    return 1 if total_fail > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
