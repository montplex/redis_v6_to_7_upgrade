# Redis v6 vs v7 Command Diff — Design Document

## Goal

Produce a structured, machine-readable comparison of every Redis command between
v6.2 and v7.2, covering input parameters (arguments), output format (reply schema),
metadata (arity, flags, ACL categories, key specs), and behavioral changes.

The approach: generate v7-format JSON descriptors for both versions from live
servers + source code, then diff them programmatically and verify against the
live v6 server.

## Architecture

```
                    ┌──────────────────┐
                    │  Redis v6 server │  (port 6399)
                    │  Redis v7 server │  (port 7399)
                    └────────┬─────────┘
                             │  COMMAND / COMMAND DOCS
                             v
               ┌─────────────────────────────┐
               │  generate_command_jsons.py   │
               │  (query live servers +       │
               │   merge v7 source JSONs)     │
               └──────┬──────────────┬────────┘
                      │              │
                      v              v
              v6_commands/    v7_commands/
              (328 files)     (370 files)
                      │              │
                      v              v
               ┌─────────────────────────────┐
               │    compare_commands.py       │──> redis_v6_v7_diff.md
               └─────────────────────────────┘
                      │
              v6_commands/
                      │
                      v
               ┌─────────────────────────────┐
               │    verify_v6_commands.py     │──> test results (stdout)
               └──────┬──────────────────────┘
                      │
                      v
                Redis v6 server (live verification)
```

## Data Sources

| Source | What it provides |
|--------|-----------------|
| v6 `COMMAND` (live) | arity, flags, ACL categories, first/last key, step — for all 224 top-level commands |
| v7 `COMMAND` (live) | Same as above + key_specs array + subcommand entries (element 9) |
| v7 `COMMAND DOCS` (live) | summary, since, group, complexity, history, arguments (full tree), subcommand docs |
| v7 source `src/commands/*.json` | reply_schema, command_tips, deprecated_since, replaced_by, doc_flags, container |

v6 has no `COMMAND DOCS` and no on-disk JSON files, so v6 JSONs are synthesized by
combining v6's `COMMAND` output with v7's `COMMAND DOCS` (filtering out anything
with `since >= 7.0.0`).

## Files

### `generate_command_jsons.py` (686 lines)

Connects to both live Redis servers and produces one JSON file per command in
`v6_commands/` and `v7_commands/`, using the same schema as v7's
`src/commands/*.json`.

**Key design decisions:**

1. **v6 subcommand derivation** — v6's `COMMAND` only returns top-level entries
   (e.g. `CONFIG` but not `CONFIG|SET`). Subcommands are derived from v7's
   `COMMAND DOCS` by checking `since < 7.0.0` on each subcommand entry. Their
   arity/flags come from v7's `COMMAND` response (element 9 = subcommand array).

2. **v7 source enrichment** — The live `COMMAND DOCS` protocol does not expose
   `reply_schema`, `command_tips`, `deprecated_since`, or `replaced_by`. These
   are read from the v7 source tree (`/home/kerry/ws/redis/src/commands/*.json`)
   and merged in.

3. **Subcommand key collision resolution** — On-disk source JSONs use short keys
   (e.g. `config-set.json` has key `"SET"`, not `"CONFIG|SET"`). The loader uses
   the `"container"` field present in every subcommand JSON to reconstruct the
   full name: `container="CONFIG"` + key `"SET"` → `"CONFIG|SET"`.

4. **Pre-v7 argument filtering** — When building v6 JSONs from v7 docs, arguments
   with `since >= 7.0.0` are recursively stripped. Similarly, history entries from
   v7 are excluded.

5. **v6 reply_schema** — For commands that existed before v7, the reply format
   didn't change, so the v7 source `reply_schema` is copied to v6 JSONs as-is
   (except for commands first introduced in v7).

**Per-command JSON schema:**

```json
{
  "COMMAND_NAME": {
    "summary": "...",
    "complexity": "O(...)",
    "group": "string | hash | list | ...",
    "since": "1.0.0",
    "arity": -3,
    "command_flags": ["WRITE", "DENYOOM"],
    "acl_categories": ["STRING", "WRITE", "SLOW"],
    "arguments": [
      {
        "name": "key",
        "type": "key",
        "key_spec_index": 0
      },
      {
        "name": "value",
        "type": "string"
      },
      {
        "name": "condition",
        "type": "oneof",
        "optional": true,
        "since": "2.6.12",
        "arguments": [
          {"name": "nx", "type": "pure-token", "token": "NX"},
          {"name": "xx", "type": "pure-token", "token": "XX"}
        ]
      }
    ],
    "key_specs": [...],
    "history": [["6.2.0", "Added the GET option."]],
    "reply_schema": {"const": "OK"},
    "deprecated_since": "6.2.0",
    "replaced_by": "...",
    "command_tips": [...]
  }
}
```

### `compare_commands.py` (517 lines)

Reads `v6_commands/` and `v7_commands/`, compares every field, and writes
`redis_v6_v7_diff.md` (3583 lines, 12 sections + summary).

**Report sections:**

| # | Section | What it compares |
|---|---------|-----------------|
| 1 | New Commands in v7 | Commands in v7 but not v6, grouped by category |
| 2 | Removed / Deprecated | Commands in v6 but not v7 |
| 3 | Subcommands in v7 | All v7 subcommands, marking new ones |
| 4 | Arity Changes | Commands where arity changed (fixed↔variable) |
| 5 | Command Flag Changes | Added/removed flags per command |
| 6 | ACL Category Changes | Added/removed ACL categories per command |
| 7 | New v7 Arguments | Arguments with `since >= 7.0.0` on pre-existing commands |
| 8 | Behavioral Changes | `history` entries from v7 on pre-existing commands |
| 9 | Input Parameter Diffs | Deep recursive argument structure diff (added/removed/changed) |
| 10 | Reply Schema Diffs | `reply_schema` differences between v6 and v7 |
| 11 | Deprecated Commands | Commands with `deprecated_since` or `doc_flags` |
| 12 | Full Argument Specs | Complete argument tree for every shared command (collapsible) |

**Argument diff algorithm** (`diff_arguments`):
- Builds name→arg maps for both versions
- Detects added, removed, and changed arguments
- For changed arguments, compares: type, token, optional, multiple, multiple_token
- Recurses into nested `arguments` (for oneof/block types)

### `verify_v6_commands.py` (625 lines)

Verifies all 328 generated v6 command JSONs against the live v6 server.
Three-part test suite:

**Part 1: Metadata verification (1630 checks, 0 failures)**

For all 224 top-level commands, fetches `COMMAND` from the live v6 server and
compares:
- `arity` — exact match
- `command_flags` — normalized flag names, sorted comparison
- `acl_categories` — normalized (strip `@` prefix, uppercase), sorted comparison
- Key positions — `first_key`, `last_key`, `key_step` from `key_specs` vs live

For all 104 subcommands, verifies presence of `summary`, `arity`, `group`, `since`.

**Part 2: Argument execution (232 checks, 0 failures, 251 skips)**

For each command with an `arguments` spec:
1. Auto-generates a minimal valid argument list by walking the argument tree
   (picks first oneof option, fills required args, skips optional ones)
2. Executes the command on the live server — expects success or a recognized
   data/state error (WRONGTYPE, NOGROUP, etc.)
3. Tests wrong-arity rejection — sends zero args to commands that need them

Custom argument overrides for commands where the generic builder can't produce
semantically valid values (stream IDs, geo units, lex ranges, SHA1 hashes).

Skips blocking commands (BLPOP, SUBSCRIBE, XREAD), destructive commands
(SHUTDOWN, FLUSHDB, CLUSTER), and internal commands (PSYNC, REPLCONF).

**Part 3: Reply schema (76 checks, 0 failures, 226 skips)**

Executes each command and checks the Python reply type against `reply_schema`:
- Handles redis-py type coercions: `OK`→`True`, SCAN→tuple, INFO→dict,
  GEODIST→float, LASTSAVE→datetime, SDIFF→set
- Schema matching supports: `const`, `type`, `anyOf`, `oneOf`, nested schemas

### `redis_v6_v7_diff.md` (3583 lines)

The generated diff report. Key findings:

| Metric | Count |
|--------|-------|
| v6 commands (top + sub) | 328 |
| v7 commands (top + sub) | 370 |
| New in v7 | 45 |
| Removed from v6 | 3 |
| Arity changes | 8 |
| Flag changes | 77 |
| ACL category changes | 19 |
| Commands with new v7 args | 8 |
| Behavioral changes | 31 |
| Argument structure diffs | 8 |
| Reply schema diffs | 0 |
| Deprecated commands | 26 |

### `v6_commands/` (328 JSON files) and `v7_commands/` (370 JSON files)

One JSON file per command/subcommand. Filename convention:
`command-name.json` for top-level, `parent-sub.json` for subcommands
(e.g. `config-set.json` for `CONFIG|SET`).

## Commands with Argument Differences (v6 vs v7)

Only 8 commands have structural argument differences — all are v7 additions,
all backward-compatible (new args are optional):

| Command | Change in v7 |
|---------|-------------|
| BITCOUNT | Added optional `BYTE`/`BIT` unit for range |
| BITPOS | Added optional `BYTE`/`BIT` unit for range |
| EXPIRE | Added optional `NX`/`XX`/`GT`/`LT` condition |
| EXPIREAT | Added optional `NX`/`XX`/`GT`/`LT` condition |
| PEXPIRE | Added optional `NX`/`XX`/`GT`/`LT` condition |
| PEXPIREAT | Added optional `NX`/`XX`/`GT`/`LT` condition |
| SHUTDOWN | Added optional `NOW`/`FORCE`/`ABORT` flags |
| XSETID | Added optional `ENTRIESADDED`/`MAXDELETEDID` params |

## Bugs Found and Fixed

1. **Source map key collision** — `load_v7_source_jsons()` initially loaded
   JSON files by their internal key name. Subcommand files like `config-set.json`
   use key `"SET"` which collided with the top-level `set.json` (also key `"SET"`).
   Fix: use the `"container"` field in subcommand JSONs to reconstruct the full
   command name (`CONFIG|SET`).

## How to Run

```bash
# Prerequisites: Redis v6 on port 6399, Redis v7 on port 7399, pip install redis

# Step 1: Generate command JSONs from live servers
python3 generate_command_jsons.py

# Step 2: Generate the diff report
python3 compare_commands.py

# Step 3: Verify v6 JSONs against live server
python3 verify_v6_commands.py
```
