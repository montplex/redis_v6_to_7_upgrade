#!/usr/bin/env python3
"""
Generate Redis command JSON files from live servers.

- v6: uses COMMAND (INFO) to get arity, flags, ACL categories, key positions
- v7: uses COMMAND (INFO) + COMMAND DOCS to get full details including
      summary, since, group, complexity, history, arguments

Output: v6_commands/ and v7_commands/ directories with one JSON file per command.
Format matches v7's src/commands/*.json schema.
"""

import json
import os
import sys
import redis

V6_PORT = 6399
V7_PORT = 7399
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
V6_OUT = os.path.join(OUTPUT_DIR, "v6_commands")
V7_OUT = os.path.join(OUTPUT_DIR, "v7_commands")

# v7 on-disk JSON source directory for reply_schema and extra fields
V7_SRC_COMMANDS = "/home/kerry/ws/redis/src/commands"

# v6 flag string -> v7 flag name mapping
FLAG_MAP = {
    "write": "WRITE",
    "readonly": "READONLY",
    "denyoom": "DENYOOM",
    "admin": "ADMIN",
    "pubsub": "PUBSUB",
    "noscript": "NOSCRIPT",
    "random": "RANDOM",
    "sort_for_script": "TO_SORT",
    "loading": "LOADING",
    "stale": "STALE",
    "no_monitor": "NO_MONITOR",
    "no_slowlog": "NO_SLOWLOG",
    "asking": "ASKING",
    "fast": "FAST",
    "no_auth": "NO_AUTH",
    "may_replicate": "MAY_REPLICATE",
    "movablekeys": "MOVABLEKEYS",
    # v7 may have additional flags
    "no_mandatory_keys": "NO_MANDATORY_KEYS",
    "no_multi": "NO_MULTI",
    "no_async_loading": "NO_ASYNC_LOADING",
    "allow_busy": "ALLOW_BUSY",
    "sentinel": "SENTINEL",
    "only_sentinel": "ONLY_SENTINEL",
    "protected": "PROTECTED",
    "touching": "TOUCHING",
}


def load_v7_source_jsons():
    """Load all v7 on-disk command JSON files from src/commands/.

    Returns a dict keyed by full uppercase command name (e.g. "SET", "CLIENT|SETINFO")
    containing the full on-disk JSON data including reply_schema, command_tips,
    deprecated_since, replaced_by, doc_flags, container, etc.

    Subcommand files (e.g. config-set.json with key "SET") are mapped to their
    full name (CONFIG|SET) by detecting the parent from the filename.
    """
    source_map = {}
    if not os.path.isdir(V7_SRC_COMMANDS):
        print(f"  WARNING: v7 source dir not found: {V7_SRC_COMMANDS}")
        return source_map

    # Load all commands, using the "container" field in subcommand files
    # to reconstruct full names (e.g. config-set.json has "container": "CONFIG"
    # and key "SET" -> full name is "CONFIG|SET")
    for fname in sorted(os.listdir(V7_SRC_COMMANDS)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(V7_SRC_COMMANDS, fname)
        with open(fpath) as f:
            data = json.load(f)

        for cmd_name, cmd_data in data.items():
            container = cmd_data.get("container")
            if container:
                # Subcommand: "container": "CONFIG", key "SET" -> "CONFIG|SET"
                full_name = f"{container}|{cmd_name}"
            else:
                full_name = cmd_name
            source_map[full_name] = cmd_data

    return source_map


def enrich_from_source(data, source_entry):
    """Enrich a generated command dict with fields from v7 on-disk source JSON.

    Adds: reply_schema, command_tips, deprecated_since, replaced_by, doc_flags.
    """
    for field in ("reply_schema", "command_tips", "deprecated_since", "replaced_by", "doc_flags"):
        if field in source_entry:
            data[field] = source_entry[field]


def get_raw_connection(port):
    """Get a raw Redis connection."""
    r = redis.Redis(port=port)
    r.ping()
    return r


def fetch_all_command_info(r):
    """Fetch COMMAND output (all commands) via raw connection."""
    conn = r.connection_pool.get_connection()
    try:
        conn.send_command("COMMAND")
        raw = conn.read_response()
    finally:
        r.connection_pool.release(conn)
    return raw


def fetch_command_docs_all(r):
    """Fetch COMMAND DOCS for all commands (v7 only)."""
    conn = r.connection_pool.get_connection()
    try:
        conn.send_command("COMMAND", "DOCS")
        raw = conn.read_response()
    finally:
        r.connection_pool.release(conn)
    return raw


def decode_bytes(obj):
    """Recursively decode bytes to str."""
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if isinstance(obj, list):
        return [decode_bytes(x) for x in obj]
    if isinstance(obj, dict):
        return {decode_bytes(k): decode_bytes(v) for k, v in obj.items()}
    return obj


def parse_command_info_entry(entry):
    """
    Parse a single COMMAND entry (array of 7-10 elements):
    [name, arity, flags, first_key, last_key, step, acl_categories, ...]
    """
    entry = decode_bytes(entry)
    name = entry[0]
    arity = entry[1]
    flags = entry[2]  # list of strings
    first_key = entry[3]
    last_key = entry[4]
    step = entry[5]
    acl_categories = entry[6] if len(entry) > 6 else []

    # Normalize flags
    normalized_flags = []
    for f in flags:
        f_lower = f.lower().replace("-", "_")
        normalized_flags.append(FLAG_MAP.get(f_lower, f.upper()))

    # Normalize ACL categories (remove @ prefix)
    normalized_acl = []
    for cat in acl_categories:
        c = cat.lstrip("@").upper()
        normalized_acl.append(c)

    # v7 has: element 7 = key_specs, element 8 = tips, element 9 = subcommands
    key_specs_raw = entry[7] if len(entry) > 7 else []
    # element 8 = tips (skip), element 9 = subcommands
    subcommands_raw = entry[9] if len(entry) > 9 else []

    return {
        "name": name,
        "arity": arity,
        "command_flags": sorted(normalized_flags),
        "acl_categories": sorted(normalized_acl),
        "first_key_pos": first_key,
        "last_key_pos": last_key,
        "key_step": step,
        "key_specs_raw": key_specs_raw,
        "subcommands_raw": subcommands_raw,
    }


def parse_key_spec(raw_spec):
    """Parse a raw key_spec array into a dict."""
    spec = decode_bytes(raw_spec)
    result = {}
    i = 0
    while i < len(spec) - 1:
        key = spec[i]
        val = spec[i + 1]
        if key == "flags":
            result["flags"] = val if isinstance(val, list) else [val]
        elif key == "begin_search":
            result["begin_search"] = parse_kv_pairs(val)
        elif key == "find_keys":
            result["find_keys"] = parse_kv_pairs(val)
        elif key == "notes":
            result["notes"] = val
        i += 2
    return result


def parse_kv_pairs(raw):
    """Parse alternating key-value pairs from a flat list into nested dict."""
    if not isinstance(raw, list):
        return raw
    result = {}
    i = 0
    while i < len(raw) - 1:
        key = raw[i]
        val = raw[i + 1]
        if isinstance(val, list) and len(val) >= 2 and isinstance(val[0], str):
            # Could be nested kv pairs
            result[key] = parse_kv_pairs(val)
        else:
            result[key] = val
        i += 2
    return result


def parse_docs_entry(raw_pairs):
    """Parse COMMAND DOCS response for a single command (alternating kv list)."""
    pairs = decode_bytes(raw_pairs)
    result = {}
    i = 0
    while i < len(pairs) - 1:
        key = pairs[i]
        val = pairs[i + 1]
        if key == "arguments":
            result["arguments"] = [parse_argument(a) for a in val]
        elif key == "subcommands":
            result["subcommands"] = parse_subcommands(val)
        elif key == "history":
            result["history"] = [[h[0], h[1]] for h in val]
        else:
            result[key] = val
        i += 2
    return result


def parse_argument(raw_arg):
    """Parse a single argument from COMMAND DOCS."""
    arg = decode_bytes(raw_arg)
    result = {}
    i = 0
    while i < len(arg) - 1:
        key = arg[i]
        val = arg[i + 1]
        if key == "arguments":
            result["arguments"] = [parse_argument(a) for a in val]
        elif key == "flags":
            result["flags"] = val if isinstance(val, list) else [val]
        elif key == "key_spec_index":
            result["key_spec_index"] = val
        else:
            result[key] = val
        i += 2

    # Convert flags list to individual fields for v7 JSON format
    flags = result.pop("flags", [])
    if "optional" in flags:
        result["optional"] = True
    if "multiple" in flags:
        result["multiple"] = True
    if "multiple_token" in flags:
        result["multiple_token"] = True

    # Remove display_text (not in the on-disk JSON format)
    result.pop("display_text", None)

    return result


def parse_subcommands(raw):
    """Parse subcommands from COMMAND DOCS."""
    result = {}
    raw = decode_bytes(raw)
    i = 0
    while i < len(raw) - 1:
        name = raw[i]
        data = raw[i + 1]
        result[name] = parse_docs_entry(data)
        i += 2
    return result


def build_fallback_key_specs(cmd_info):
    """Build key_specs from parsed COMMAND info when richer docs are unavailable."""
    if cmd_info["key_specs_raw"]:
        parsed_specs = [s for s in (parse_key_spec(ks) for ks in cmd_info["key_specs_raw"] if ks) if s]
        if parsed_specs:
            return parsed_specs

    if cmd_info["first_key_pos"] <= 0:
        return None

    command_flags = set(cmd_info.get("command_flags", []))
    if "READONLY" in command_flags and "WRITE" not in command_flags:
        flags = ["RO", "ACCESS"]
    elif "WRITE" in command_flags:
        flags = ["RW", "UPDATE"]
    else:
        flags = ["RW"]

    return [
        {
            "flags": flags,
            "begin_search": {"index": {"pos": cmd_info["first_key_pos"]}},
            "find_keys": {
                "range": {
                    "lastkey": cmd_info["last_key_pos"],
                    "step": cmd_info["key_step"],
                    "limit": 0,
                }
            },
        }
    ]


def build_v6_json(cmd_info, docs_data=None):
    """Build a v7-format JSON dict from v6 COMMAND INFO data.

    If docs_data (from v7 COMMAND DOCS) is provided, enrich with
    summary, since, group, complexity, and pre-v7 arguments.
    """
    name = cmd_info["name"].upper()

    data = {
        "summary": "",
        "complexity": "",
        "group": "",
        "since": "",
        "arity": cmd_info["arity"],
        "command_flags": cmd_info["command_flags"],
        "acl_categories": cmd_info["acl_categories"],
    }

    # Enrich from v7 docs if available
    if docs_data:
        data["summary"] = docs_data.get("summary", "")
        data["complexity"] = docs_data.get("complexity", "")
        data["group"] = docs_data.get("group", "")
        data["since"] = docs_data.get("since", "")

        # Include arguments that existed before v7
        args = docs_data.get("arguments", [])
        if args:
            filtered = filter_pre_v7_args(args)
            if filtered:
                data["arguments"] = filtered

        # History entries before v7
        history = docs_data.get("history", [])
        pre_v7_hist = [h for h in history if not is_v7_version_str(h[0])]
        if pre_v7_hist:
            data["history"] = pre_v7_hist

    key_specs = build_fallback_key_specs(cmd_info)
    if key_specs:
        data["key_specs"] = key_specs

    return {name: data}


def build_v7_json(cmd_info, docs_data):
    """Build a v7-format JSON dict from v7 COMMAND INFO + COMMAND DOCS."""
    name = cmd_info["name"].upper()

    data = {
        "summary": docs_data.get("summary", ""),
        "complexity": docs_data.get("complexity", ""),
        "group": docs_data.get("group", ""),
        "since": docs_data.get("since", ""),
        "arity": cmd_info["arity"],
        "command_flags": cmd_info["command_flags"],
        "acl_categories": cmd_info["acl_categories"],
    }

    if docs_data.get("history"):
        data["history"] = docs_data["history"]

    key_specs = build_fallback_key_specs(cmd_info)
    if key_specs:
        data["key_specs"] = key_specs

    if docs_data.get("arguments"):
        data["arguments"] = docs_data["arguments"]

    return {name: data}


def write_json_file(out_dir, cmd_name, data):
    """Write a single command JSON file."""
    # Use the command name as filename, replacing spaces with hyphens for subcommands
    filename = cmd_name.lower().replace(" ", "-").replace("|", "-").replace(":", "_") + ".json"
    filepath = os.path.join(out_dir, filename)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def process_v6(r, r7=None, v7_source_map=None):
    """Process all v6 commands and generate JSON files.

    v6's COMMAND only returns top-level commands, not subcommands.
    If r7 is provided, we derive v6 subcommands from v7's COMMAND DOCS
    for any subcommand with since < 7.0.0.
    v7_source_map provides reply_schema and extra fields from v7 on-disk JSONs.
    """
    os.makedirs(V6_OUT, exist_ok=True)
    if v7_source_map is None:
        v7_source_map = {}

    print("Fetching v6 COMMAND data...")
    raw_commands = fetch_all_command_info(r)
    print(f"  Got {len(raw_commands)} top-level command entries")

    # Pre-fetch v7 docs for enrichment
    docs_map = {}
    raw_v7_commands = []
    if r7:
        print("  Fetching v7 COMMAND DOCS to enrich v6 data...")
        raw_v7_commands = fetch_all_command_info(r7)
        raw_v7_docs = fetch_command_docs_all(r7)
        decoded_docs = decode_bytes(raw_v7_docs)
        i = 0
        while i < len(decoded_docs) - 1:
            docs_map[decoded_docs[i]] = parse_docs_entry(decoded_docs[i + 1])
            i += 2

    count = 0
    v6_parent_names = set()
    for entry in raw_commands:
        info = parse_command_info_entry(entry)
        # Enrich with v7 docs if command existed before v7
        cmd_docs = docs_map.get(info["name"])
        if cmd_docs and not is_v7_version_str(cmd_docs.get("since", "")):
            json_data = build_v6_json(info, cmd_docs)
        else:
            json_data = build_v6_json(info)
        # Enrich with reply_schema from v7 source for pre-v7 commands
        cmd_key = info["name"].upper()
        src = v7_source_map.get(cmd_key)
        if src and not is_v7_version_str(src.get("since", "")):
            if "reply_schema" in src:
                json_data[cmd_key]["reply_schema"] = src["reply_schema"]
            if "deprecated_since" in src and not is_v7_version_str(src["deprecated_since"]):
                json_data[cmd_key]["deprecated_since"] = src["deprecated_since"]
            if "replaced_by" in src:
                json_data[cmd_key]["replaced_by"] = src["replaced_by"]
        write_json_file(V6_OUT, info["name"], json_data)
        v6_parent_names.add(info["name"])
        count += 1

    # Derive subcommands from v7's COMMAND DOCS + COMMAND INFO
    sub_count = 0
    if r7:
        print("  Deriving v6 subcommands from v7 data...")
        # Build subcommand info from v7 COMMAND output (element 9)
        v7_sub_info_map = {}
        for entry in raw_v7_commands:
            info = parse_command_info_entry(entry)
            subs = entry[9] if len(entry) > 9 else []
            if subs:
                for sub_entry in subs:
                    si = parse_command_info_entry(sub_entry)
                    v7_sub_info_map[si["name"]] = si

        # For each v7 parent that also exists in v6, check subcommands
        for entry in raw_v7_commands:
            info = parse_command_info_entry(entry)
            parent_name = info["name"]
            if parent_name not in v6_parent_names:
                continue

            docs = docs_map.get(parent_name, {})
            sub_docs_map = docs.get("subcommands", {})

            for sub_name, sub_docs in sub_docs_map.items():
                since = sub_docs.get("since", "")
                try:
                    major = int(since.split(".")[0])
                except (ValueError, IndexError):
                    major = 0

                if major >= 7:
                    continue  # This subcommand didn't exist in v6

                # Build v6 JSON for this subcommand
                # Use v7 COMMAND INFO for arity/flags if available
                si = v7_sub_info_map.get(sub_name, {
                    "name": sub_name,
                    "arity": sub_docs.get("arity", 0),
                    "command_flags": [],
                    "acl_categories": [],
                    "first_key_pos": 0,
                    "last_key_pos": 0,
                    "key_step": 0,
                    "key_specs_raw": [],
                    "subcommands_raw": [],
                })

                # Build JSON with docs info (summary, since, group, args existed in v6 too)
                cmd_key = sub_name.upper().replace("|", "|")
                data = {
                    "summary": sub_docs.get("summary", ""),
                    "complexity": sub_docs.get("complexity", ""),
                    "group": sub_docs.get("group", ""),
                    "since": since,
                    "arity": si.get("arity", 0),
                    "command_flags": si.get("command_flags", []),
                    "acl_categories": si.get("acl_categories", []),
                }

                # Include arguments that existed before v7
                args = sub_docs.get("arguments", [])
                if args:
                    filtered = filter_pre_v7_args(args)
                    if filtered:
                        data["arguments"] = filtered

                # History entries before v7
                history = sub_docs.get("history", [])
                pre_v7_hist = [h for h in history if not is_v7_version_str(h[0])]
                if pre_v7_hist:
                    data["history"] = pre_v7_hist

                key_specs = build_fallback_key_specs(si)
                if key_specs:
                    data["key_specs"] = key_specs

                # Enrich with reply_schema from v7 source for pre-v7 subcommands
                src = v7_source_map.get(cmd_key)
                if src and not is_v7_version_str(src.get("since", "")):
                    if "reply_schema" in src:
                        data["reply_schema"] = src["reply_schema"]

                json_data = {cmd_key: data}
                file_name = sub_name.replace("|", "-")
                write_json_file(V6_OUT, file_name, json_data)
                sub_count += 1

        print(f"  Derived {sub_count} subcommands for v6")

    total = count + sub_count
    print(f"  Wrote {total} JSON files to {V6_OUT} ({count} top-level + {sub_count} subcommands)")
    return total


def is_v7_version_str(ver):
    """Check if version string is >= 7.0.0."""
    try:
        return int(ver.split(".")[0]) >= 7
    except (ValueError, IndexError, AttributeError):
        return False


def filter_pre_v7_args(arguments):
    """Return arguments that existed before v7, recursively filtering nested args."""
    result = []
    for arg in arguments:
        since = arg.get("since", "")
        if is_v7_version_str(since):
            continue  # This arg was added in v7
        new_arg = dict(arg)
        if "arguments" in new_arg:
            new_arg["arguments"] = filter_pre_v7_args(new_arg["arguments"])
            if not new_arg["arguments"]:
                del new_arg["arguments"]
        result.append(new_arg)
    return result


def process_v7(r, v7_source_map=None):
    """Process all v7 commands and generate JSON files."""
    os.makedirs(V7_OUT, exist_ok=True)
    if v7_source_map is None:
        v7_source_map = {}

    print("Fetching v7 COMMAND data...")
    raw_commands = fetch_all_command_info(r)
    print(f"  Got {len(raw_commands)} command entries")

    print("Fetching v7 COMMAND DOCS data...")
    raw_docs = fetch_command_docs_all(r)
    # raw_docs is a flat list: [name1, data1, name2, data2, ...]
    docs_map = {}
    raw_docs = decode_bytes(raw_docs)
    i = 0
    while i < len(raw_docs) - 1:
        cmd_name = raw_docs[i]
        cmd_data = raw_docs[i + 1]
        docs_map[cmd_name] = parse_docs_entry(cmd_data)
        i += 2
    print(f"  Got docs for {len(docs_map)} commands")

    enriched_count = 0
    count = 0
    for entry in raw_commands:
        info = parse_command_info_entry(entry)
        name = info["name"]
        docs = docs_map.get(name, {})

        json_data = build_v7_json(info, docs)
        # Enrich with on-disk source data (reply_schema, command_tips, etc.)
        cmd_key = name.upper()
        if cmd_key in v7_source_map:
            enrich_from_source(json_data[cmd_key], v7_source_map[cmd_key])
            enriched_count += 1
        write_json_file(V7_OUT, name, json_data)
        count += 1

        # Process subcommands: merge COMMAND INFO (arity/flags) with DOCS (summary/args)
        # Build a lookup from COMMAND INFO subcommands (element 9)
        sub_info_map = {}
        if info["subcommands_raw"]:
            for sub_entry in info["subcommands_raw"]:
                si = parse_command_info_entry(sub_entry)
                sub_info_map[si["name"]] = si

        # Get subcommand docs
        sub_docs_map = docs.get("subcommands", {})

        # Merge all subcommand names from both sources
        all_sub_names = set(sub_info_map.keys()) | set(sub_docs_map.keys())
        for sub_name in sorted(all_sub_names):
            si = sub_info_map.get(sub_name, {
                "name": sub_name,
                "arity": 0,
                "command_flags": [],
                "acl_categories": [],
                "first_key_pos": 0,
                "last_key_pos": 0,
                "key_step": 0,
                "key_specs_raw": [],
                "subcommands_raw": [],
            })
            sd = sub_docs_map.get(sub_name, {})
            sub_json = build_v7_json(si, sd)
            # Enrich subcommand from on-disk source
            sub_key = sub_name.upper().replace("|", "|")
            if sub_key in v7_source_map:
                enrich_from_source(sub_json[sub_key], v7_source_map[sub_key])
                enriched_count += 1
            file_name = sub_name.replace("|", "-")
            write_json_file(V7_OUT, file_name, sub_json)
            count += 1

    print(f"  Wrote {count} JSON files to {V7_OUT} ({enriched_count} enriched from source)")
    return count


def main():
    print("=== Redis Command JSON Generator ===\n")

    try:
        r6 = get_raw_connection(V6_PORT)
        v6_version = r6.info("server").get("redis_version", "unknown")
        print(f"Connected to v6 server (port {V6_PORT}), version: {v6_version}")
    except Exception as e:
        print(f"ERROR: Cannot connect to v6 server on port {V6_PORT}: {e}")
        sys.exit(1)

    try:
        r7 = get_raw_connection(V7_PORT)
        v7_version = r7.info("server").get("redis_version", "unknown")
        print(f"Connected to v7 server (port {V7_PORT}), version: {v7_version}")
    except Exception as e:
        print(f"ERROR: Cannot connect to v7 server on port {V7_PORT}: {e}")
        sys.exit(1)

    # Load v7 on-disk source JSONs for reply_schema and extra fields
    print("Loading v7 source command JSONs...")
    v7_source_map = load_v7_source_jsons()
    print(f"  Loaded {len(v7_source_map)} command definitions from {V7_SRC_COMMANDS}")

    print()
    v7_count = process_v7(r7, v7_source_map)
    print()
    v6_count = process_v6(r6, r7, v7_source_map)  # Pass r7 and source map

    print(f"\nDone! Generated {v6_count} v6 files and {v7_count} v7 files.")
    print(f"  v6: {V6_OUT}/")
    print(f"  v7: {V7_OUT}/")


if __name__ == "__main__":
    main()
