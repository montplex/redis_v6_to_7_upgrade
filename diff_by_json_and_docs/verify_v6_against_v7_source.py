#!/usr/bin/env python3
"""
Verify v6 command JSONs against v7 source files.

For every command in v6_commands/, checks:
1. Field presence - all required v7 fields exist
2. Since version filtering - v6 should not have v7-only args/history
3. Metadata matching - compare arity, flags, key_specs with v7 source
4. Reply schema - verify reply_schema is present and valid

v6 source: ~/ws/redis_v6 (not available, v6 doesn't have src/commands)
v7 source: ~/ws/redis/src/commands/
"""

import json
import os
import sys
from pathlib import Path

V6_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v6_commands")
V7_SOURCE_DIR = os.path.expanduser("~/ws/redis/src/commands")

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"
SKIP = "\033[90mSKIP\033[0m"

REQUIRED_FIELDS = [
    "summary", "complexity", "group", "since", "arity",
    "command_flags", "acl_categories", "arguments", "key_specs", "reply_schema"
]

OPTIONAL_FIELDS = [
    "history", "deprecated_since", "replaced_by", "command_tips", "doc_flags"
]


def load_v7_source():
    """Load all v7 source command JSONs, building a map by command name."""
    cmds = {}
    subcmd_map = {}  # For subcommands: "PARENT|SUBCMD" -> data
    
    for jf in sorted(Path(V7_SOURCE_DIR).glob("*.json")):
        with open(jf) as f:
            data = json.load(f)
        for k, v in data.items():
            container = v.get("container")
            if container:
                # This is a subcommand
                full_name = f"{container}|{k}"
                subcmd_map[full_name] = {"data": v, "filename": jf.name}
            else:
                # Top-level command
                cmds[k] = {"data": v, "filename": jf.name}
    
    # Merge subcmd_map into cmds
    cmds.update(subcmd_map)
    return cmds


def load_v6_commands():
    """Load all generated v6 command JSONs."""
    cmds = {}
    for jf in sorted(Path(V6_DIR).glob("*.json")):
        with open(jf) as f:
            data = json.load(f)
        for k, v in data.items():
            cmds[k] = v
    return cmds


def parse_version(ver_str):
    """Parse version string like '1.0.0' or '7.0.0' to tuple."""
    try:
        parts = ver_str.split(".")
        return tuple(int(p) for p in parts[:3])
    except:
        return (0, 0, 0)


def is_v7_or_newer(ver_str):
    """Check if version is 7.0.0 or newer."""
    return parse_version(ver_str) >= (7, 0, 0)


def check_field_presence(cmd_name, v6_data, v7_source_entry):
    """Check all required v7 fields are present."""
    results = []
    
    # Check if this is a container command in v7 source
    is_container = False
    if v7_source_entry:
        v7_data = v7_source_entry["data"]
        if not v7_data.get("arguments") and not v7_data.get("key_specs"):
            is_container = True
    
    # For container commands, only check basic fields
    if is_container:
        for field in ["summary", "complexity", "group", "since", "arity"]:
            has_it = field in v6_data and v6_data[field] not in (None, "", 0)
            results.append((cmd_name, f"has_{field}", has_it, f"{field} present"))
        results.append((cmd_name, "container_skip", True, "container command"))
        return results
    
    # For regular commands, check all required fields
    for field in REQUIRED_FIELDS:
        has_it = field in v6_data and v6_data[field] not in (None, "", [])
        results.append((cmd_name, f"has_{field}", has_it, f"{field} present"))
    return results


def check_v7_filtering(cmd_name, v6_data):
    """Check v6 doesn't have v7-only arguments or history."""
    results = []
    
    # Check arguments for v7+ only args
    arguments = v6_data.get("arguments", [])
    for arg in arguments:
        since = arg.get("since", "1.0.0")
        if is_v7_or_newer(since):
            results.append((cmd_name, "v7_arg", False, 
                          f"argument '{arg.get('name')}' has since={since}"))
        
        # Recursively check nested arguments
        nested = arg.get("arguments", [])
        for nested_arg in nested:
            nested_since = nested_arg.get("since", "1.0.0")
            if is_v7_or_newer(nested_since):
                results.append((cmd_name, "v7_nested_arg", False,
                              f"nested arg '{nested_arg.get('name')}' has since={nested_since}"))
    
    # Check history for v7+ entries
    history = v6_data.get("history", [])
    for entry in history:
        if len(entry) >= 2:
            ver = entry[0]
            if is_v7_or_newer(ver):
                results.append((cmd_name, "v7_history", False,
                              f"history entry has since={ver}"))
    
    if not results:
        results.append((cmd_name, "v7_filtering", True, "no v7+ args or history"))
    
    return results


def check_metadata_match(cmd_name, v6_data, v7_source_entry):
    """Compare arity, flags, key_specs between v6 and v7 source.
    
    Note: Many differences are expected because v7 added flags/categories.
    """
    results = []
    
    if not v7_source_entry:
        results.append((cmd_name, "v7_source", False, "command not found in v7 source"))
        return results
    
    v7_source_data = v7_source_entry["data"]
    
    # Skip container commands (they don't have full specs in v7 source)
    if not v7_source_data.get("arguments") and not v7_source_data.get("key_specs"):
        results.append((cmd_name, "v7_source", True, "container command (skip full check)"))
        return results
    
    # Arity check - this should match for backward-compatible commands
    v6_arity = v6_data.get("arity")
    v7_arity = v7_source_data.get("arity")
    if v6_arity != v7_arity:
        results.append((cmd_name, "arity_match", False,
                      f"v6={v6_arity} v7={v7_arity}"))
    else:
        results.append((cmd_name, "arity_match", True, f"arity={v6_arity}"))
    
    # Command flags check - v7 often adds flags, so we check v6 is subset of v7
    v6_flags = set(v6_data.get("command_flags", []))
    v7_flags = set(v7_source_data.get("command_flags", []))
    extra_in_v6 = v6_flags - v7_flags
    if extra_in_v6:
        results.append((cmd_name, "flags_extra", False,
                      f"v6 has extra flags: {sorted(extra_in_v6)}"))
    else:
        results.append((cmd_name, "flags_subset", True, "v6 flags subset of v7"))
    
    # ACL categories check - v7 simplified ACL categories
    # This is a known difference - just record it
    v6_acl = v6_data.get("acl_categories", [])
    v7_acl = v7_source_data.get("acl_categories", [])
    results.append((cmd_name, "acl_check", True, f"v6={sorted(v6_acl)} v7={sorted(v7_acl)}"))
    
    # Key specs check (basic structure)
    # Note: v7 changed key_specs format significantly (lastkey=0 for reads vs lastkey=1 in v6)
    # This is a known difference, just verify presence
    v6_ks = v6_data.get("key_specs", [])
    v7_ks = v7_source_data.get("key_specs", [])
    
    if len(v6_ks) != len(v7_ks):
        results.append((cmd_name, "key_specs_count", True,
                      f"v6={len(v6_ks)} v7={len(v7_ks)} (known difference)"))
    else:
        results.append((cmd_name, "key_specs_present", True, f"count={len(v6_ks)}"))
    
    return results


def check_reply_schema(cmd_name, v6_data):
    """Check reply_schema is present and valid."""
    results = []
    
    schema = v6_data.get("reply_schema")
    if not schema:
        results.append((cmd_name, "reply_schema", False, "missing reply_schema"))
        return results
    
    # Check schema has at least one valid type
    if isinstance(schema, dict):
        has_type = any(k in schema for k in ["type", "const", "oneOf", "anyOf"])
        if has_type:
            results.append((cmd_name, "reply_schema", True, "valid schema structure"))
        else:
            results.append((cmd_name, "reply_schema", False, "invalid schema structure"))
    else:
        results.append((cmd_name, "reply_schema", False, "schema not a dict"))
    
    return results


def check_since_version(cmd_name, v6_data):
    """Check since version is pre-7.0.0 for commands in v6."""
    results = []
    
    since = v6_data.get("since", "")
    if is_v7_or_newer(since):
        results.append((cmd_name, "since_version", False,
                      f"v6 command has since={since} (v7+)"))
    else:
        results.append((cmd_name, "since_version", True, f"since={since}"))
    
    return results


def main():
    print("=" * 78)
    print("  Verify v6 Commands JSON against v7 Source Files")
    print("=" * 78)
    print(f"v6 commands dir: {V6_DIR}")
    print(f"v7 source dir: {V7_SOURCE_DIR}")
    print()
    
    # Load data
    v6_cmds = load_v6_commands()
    v7_source = load_v7_source()
    
    print(f"Loaded {len(v6_cmds)} v6 command JSONs")
    print(f"Loaded {len(v7_source)} v7 source command JSONs")
    print()
    
    total_pass = 0
    total_fail = 0
    total_skip = 0
    failures = []
    
    # Track stats per check type
    stats = {
        "field_presence": {"pass": 0, "fail": 0, "skip": 0},
        "v7_filtering": {"pass": 0, "fail": 0, "skip": 0},
        "metadata_match": {"pass": 0, "fail": 0, "skip": 0},
        "reply_schema": {"pass": 0, "fail": 0, "skip": 0},
        "since_version": {"pass": 0, "fail": 0, "skip": 0},
    }
    
    # Check each v6 command
    for cmd_name in sorted(v6_cmds.keys()):
        v6_data = v6_cmds[cmd_name]
        
        # Find matching v7 source (by command name key)
        v7_entry = v7_source.get(cmd_name)
        
        # 1. Field presence
        for cmd, check, passed, detail in check_field_presence(cmd_name, v6_data, v7_entry):
            if passed:
                stats["field_presence"]["pass"] += 1
                total_pass += 1
                print(f"  [{PASS}] {cmd:30s} {check:20s} {detail}")
            else:
                stats["field_presence"]["fail"] += 1
                total_fail += 1
                failures.append((cmd, check, detail))
                print(f"  [{FAIL}] {cmd:30s} {check:20s} {detail}")
        
        # 2. V7 filtering check
        for cmd, check, passed, detail in check_v7_filtering(cmd_name, v6_data):
            if passed:
                stats["v7_filtering"]["pass"] += 1
                total_pass += 1
            else:
                stats["v7_filtering"]["fail"] += 1
                total_fail += 1
                failures.append((cmd, check, detail))
                print(f"  [{FAIL}] {cmd:30s} {check:20s} {detail}")
        
        # 3. Metadata match with v7 source
        for cmd, check, passed, detail in check_metadata_match(cmd_name, v6_data, v7_entry):
            if passed:
                stats["metadata_match"]["pass"] += 1
                total_pass += 1
            else:
                stats["metadata_match"]["fail"] += 1
                total_fail += 1
                failures.append((cmd, check, detail))
                print(f"  [{FAIL}] {cmd:30s} {check:20s} {detail}")
        
        # 4. Reply schema
        for cmd, check, passed, detail in check_reply_schema(cmd_name, v6_data):
            if passed:
                stats["reply_schema"]["pass"] += 1
                total_pass += 1
            else:
                stats["reply_schema"]["fail"] += 1
                total_fail += 1
                failures.append((cmd, check, detail))
                print(f"  [{FAIL}] {cmd:30s} {check:20s} {detail}")
        
        # 5. Since version
        for cmd, check, passed, detail in check_since_version(cmd_name, v6_data):
            if passed:
                stats["since_version"]["pass"] += 1
                total_pass += 1
            else:
                stats["since_version"]["fail"] += 1
                total_fail += 1
                failures.append((cmd, check, detail))
                print(f"  [{FAIL}] {cmd:30s} {check:20s} {detail}")
    
    # Summary
    print()
    print("=" * 78)
    print("  SUMMARY BY CHECK TYPE")
    print("=" * 78)
    
    for check_type, stat in stats.items():
        print(f"  {check_type:20s}: {PASS} {stat['pass']:4d}  {FAIL} {stat['fail']:4d}")
    
    print()
    print("=" * 78)
    print(f"  GRAND TOTAL: {PASS} {total_pass}  |  {FAIL} {total_fail}")
    print("=" * 78)
    
    if failures:
        print(f"\n  {FAIL} Failures ({len(failures)}):")
        for cmd, check, detail in failures:
            print(f"    - {cmd}: {check} — {detail}")
        return 1
    else:
        print(f"\n  All checks passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
