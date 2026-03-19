# Redis v6 to v7 Command Diff

## Goal

Generate a machine-readable command catalog for Redis 6.2 and Redis 7.2+,
compare them, and produce a trustworthy upgrade report covering:

- command additions and removals
- arity, flags, ACL categories, and key-spec changes
- argument and behavior changes
- reply schema differences

The primary output is a verified `v6_commands/` directory, a `v7_commands/`
directory, and a generated diff report in `redis_v6_v7_diff.md`.

## Trusted Workflow

This is the workflow that was verified in practice and should be treated as the
main path for this project:

1. Start a live Redis v6 server on `127.0.0.1:6399`.
2. Start a live Redis v7 server on `127.0.0.1:7399`.
3. Run `generate_command_jsons.py` to regenerate `v6_commands/` and `v7_commands/`.
4. Run `compare_commands.py` to regenerate `redis_v6_v7_diff.md`.
5. Run `verify_v6_commands.py` to validate the generated v6 JSON files against
   the live Redis v6 server.

That path was run successfully with:

- Redis v6.2.6 on port `6399`
- Redis v7.2.11 on port `7399`
- `verify_v6_commands.py` result:
  `PASS 1938 | FAIL 0 | SKIP 477`

## Architecture

```text
Redis v6 live server (6399) ─┐
                             ├─ generate_command_jsons.py ──> v6_commands/
Redis v7 live server (7399) ─┤                             └─> v7_commands/
                             │
Redis v7 source JSONs   ─────┘

v6_commands/ + v7_commands/
        └─ compare_commands.py ──> redis_v6_v7_diff.md

v6_commands/ + live Redis v6
        └─ verify_v6_commands.py
```

## Data Sources

| Source | Purpose |
|---|---|
| live Redis v6 `COMMAND` | authoritative v6 arity, flags, ACL categories, and key positions |
| live Redis v7 `COMMAND` | authoritative v7 command metadata, key specs, and subcommand info |
| live Redis v7 `COMMAND DOCS` | summaries, groups, complexity, history, and argument trees |
| Redis v7 source `src/commands/*.json` | reply schemas and source-only fields not exposed by `COMMAND DOCS` |
| Redis v6 source tree `~/ws/redis_v6/src` | reference for v6-only commands like `HOST:`, `POST`, and `STRALGO` |

Important constraint:

- Redis v6 does not have `COMMAND DOCS` and does not ship the newer
  `src/commands/*.json` command metadata format.
- Because of that, v6 JSON files are synthesized from live v6 `COMMAND` plus
  v7 `COMMAND DOCS`, while filtering out anything introduced in Redis 7.

## Output Model

Each generated command file follows the Redis v7 command JSON shape as closely
as possible. Typical fields include:

- `summary`
- `complexity`
- `group`
- `since`
- `arity`
- `command_flags`
- `acl_categories`
- `arguments`
- `key_specs`
- `history`
- `reply_schema`
- `deprecated_since`
- `replaced_by`
- `command_tips`

For v6, some fields are synthesized rather than sourced directly:

- `arguments` and `history` come from v7 docs, filtered to pre-7 entries only
- `reply_schema` is copied from v7 source when the command existed before v7
- `key_specs` are reconstructed from live positional metadata when richer specs
  are not available

## Primary Scripts

### `generate_command_jsons.py`

Use this first whenever command JSONs need to be refreshed.

What it does:

- connects to Redis v6 on port `6399`
- connects to Redis v7 on port `7399`
- reads live command metadata from both servers
- reads Redis v7 source JSON files from `/home/kerry/ws/redis/src/commands`
- writes one JSON file per command into `v6_commands/` and `v7_commands/`

Key behavior:

- derives v6 subcommands from v7 command docs when the subcommand `since` is
  pre-7
- reconstructs full subcommand names using the v7 source `container` field
- strips v7-only arguments and history from v6 output
- synthesizes fallback `key_specs`
- preserves readonly semantics in fallback `key_specs` by using `RO/ACCESS`
  for readonly commands and `RW/UPDATE` for write commands

When to use it:

- after changing generation logic
- after changing Redis server versions
- before regenerating the diff report
- before re-running verification

How to run:

```bash
python3 generate_command_jsons.py
```

### `compare_commands.py`

Use this after JSON generation to rebuild the human-readable upgrade report.

What it does:

- reads all files from `v6_commands/` and `v7_commands/`
- compares shared commands and identifies additions/removals
- writes `redis_v6_v7_diff.md`

Report sections include:

- new commands in v7
- removed commands from v6
- v7 subcommands
- arity changes
- command flag changes
- ACL category changes
- new v7 arguments
- behavioral changes from history entries
- recursive argument diffs
- reply schema diffs
- deprecated commands
- full argument trees

When to use it:

- after any regeneration of command JSONs
- before publishing or reviewing the upgrade report

How to run:

```bash
python3 compare_commands.py
```

### `verify_v6_commands.py`

This is the authoritative verifier for the generated v6 JSON files.

What it does:

- validates top-level metadata against live Redis v6 `COMMAND`
- checks that subcommands have required descriptive fields
- generates minimal valid argument lists and executes safe commands
- checks wrong-arity handling
- validates reply values against `reply_schema` where safe

Why it is trusted:

- it compares generated output directly against a live Redis v6 server
- it was run successfully on regenerated output with `0` failures

When to use it:

- after every regeneration of `v6_commands/`
- before claiming the v6 JSON set is correct

How to run:

```bash
python3 verify_v6_commands.py
```

## Secondary / Legacy Scripts

These scripts are still useful, but they are not the primary source of truth.
Keep them for exploration, sanity checks, and compatibility experiments.

### `verify_v6_against_v7_source.py`

Purpose:

- structural sanity check of v6 JSON files against v7 source command files

Why it is not authoritative:

- it assumes too much symmetry between v6 and v7
- it reports expected version differences as failures
- it flags legitimate v6-only commands not present in v7 source
- it treats some missing `reply_schema` or arity differences as bugs even when
  they are correct for Redis 6

Use it when:

- investigating suspicious generated output
- auditing field coverage
- checking that v7-only arguments/history did not leak into v6 JSON

Do not use it as the final pass/fail decision for correctness.

### `test_v6_on_v7.py`

Purpose:

- execute v6 commands against a live Redis v7 server to check backward
  compatibility at a practical level

Why it is secondary:

- this is a compatibility smoke test, not a generator verifier
- many commands are skipped because they are destructive, blocking, or need
  special setup
- a passing result says more about runtime compatibility than JSON correctness

Use it when:

- validating upgrade compatibility expectations
- checking whether v6 command shapes are still accepted by Redis v7

### `execute_v6_on_v7_full.py`

Purpose:

- broader compatibility probing using fuller generated argument sets on Redis v7

Why it is secondary:

- generated argument lists are heuristic, not authoritative
- it is more exploratory and can produce noisy data/state errors
- it is better for surfacing interesting incompatibilities than for proving
  correctness

Use it when:

- exploring command behavior on Redis v7
- looking for edge cases missed by minimal-argument compatibility checks

### `test_generate_command_jsons.py`

Purpose:

- focused regression tests for the generator implementation

Current coverage:

- fallback `key_specs` generation for readonly vs write commands

Use it when:

- changing generation logic
- fixing generator bugs
- before regenerating the command directories

How to run:

```bash
python3 -m unittest -v test_generate_command_jsons.py
```

## Known Edge Cases

### v6-only commands

The generated v6 set intentionally includes commands that do not exist in Redis
v7 source metadata, including:

- `HOST:`
- `POST`
- `STRALGO`

These are real Redis 6 commands and should remain in `v6_commands/`. They show
up in the diff report as removed commands.

### Skipped live checks

`verify_v6_commands.py` skips commands that are:

- blocking
- destructive
- replication/internal
- pubsub-mode commands
- commands requiring special server setup

That is expected. Those commands still receive metadata checks where possible.

## Verified Usage

Typical end-to-end usage:

```bash
# 1. Start Redis v6 and v7 servers on 6399 and 7399

# 2. Optional: verify generator regression tests
python3 -m unittest -v test_generate_command_jsons.py

# 3. Regenerate JSON command catalogs
python3 generate_command_jsons.py

# 4. Rebuild the diff report
python3 compare_commands.py

# 5. Verify v6 JSONs against live Redis v6
python3 verify_v6_commands.py

# 6. Optional exploratory checks
python3 verify_v6_against_v7_source.py
python3 test_v6_on_v7.py
python3 execute_v6_on_v7_full.py
```

## Current Expected Totals

From the current generated output:

| Metric | Count |
|---|---:|
| v6 commands | 328 |
| v7 commands | 370 |
| v6 top-level commands | 224 |
| v6 subcommands | 104 |
| v7 top-level commands | 241 |
| v7 subcommands | 129 |
| new in v7 | 45 |
| removed from v6 | 3 |
| arity changes | 8 |
| flag changes | 77 |
| ACL category changes | 19 |
| argument structure diffs | 8 |
| reply schema diffs | 0 |
| deprecated commands | 26 |

## Summary

If you need a reliable answer to "are the generated Redis v6 JSON files correct
for a live Redis 6 server?", the correct workflow is:

1. `python3 generate_command_jsons.py`
2. `python3 verify_v6_commands.py`

If you need the human-readable upgrade report, add:

3. `python3 compare_commands.py`

Everything else in this directory is supplementary.
