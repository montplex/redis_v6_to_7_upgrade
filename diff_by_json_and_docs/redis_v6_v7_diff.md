# Redis v6.2 → v7.2 Command Differences

- v6 total: **328** (224 top-level + 104 subcommands)
- v7 total: **370** (241 top-level + 129 subcommands)

---
## 1. New Commands in v7

### cluster

| Command | Since | Arity | Summary |
|---------|-------|-------|---------|
| `CLUSTER|ADDSLOTSRANGE` | 7.0.0 | -4 | Assigns new hash slot ranges to a node. |
| `CLUSTER|DELSLOTSRANGE` | 7.0.0 | -4 | Sets hash slot ranges as unbound for a node. |
| `CLUSTER|LINKS` | 7.0.0 | 2 | Returns a list of all TCP links to and from peer nodes. |
| `CLUSTER|MYSHARDID` | 7.2.0 | 2 | Returns the shard ID of a node. |
| `CLUSTER|SHARDS` | 7.0.0 | 2 | Returns the mapping of cluster slots to shards. |

### connection

| Command | Since | Arity | Summary |
|---------|-------|-------|---------|
| `CLIENT|NO-EVICT` | 7.0.0 | 3 | Sets the client eviction mode of the connection. |
| `CLIENT|NO-TOUCH` | 7.2.0 | 3 | Controls whether commands sent by the client affect the LRU/LFU of accessed keys. |
| `CLIENT|SETINFO` | 7.2.0 | 4 | Sets information specific to the client or connection. |
| `QUIT` | 1.0.0 | -1 | Closes the connection. |

### generic

| Command | Since | Arity | Summary |
|---------|-------|-------|---------|
| `EXPIRETIME` | 7.0.0 | 2 | Returns the expiration time of a key as a Unix timestamp. |
| `PEXPIRETIME` | 7.0.0 | 2 | Returns the expiration time of a key as a Unix milliseconds timestamp. |
| `SORT_RO` | 7.0.0 | -2 | Returns the sorted elements of a list, a set, or a sorted set. |
| `WAITAOF` | 7.2.0 | 4 | Blocks until all of the preceding write commands sent by the connection are written to the append-only file of the master and/or replicas. |

### list

| Command | Since | Arity | Summary |
|---------|-------|-------|---------|
| `BLMPOP` | 7.0.0 | -5 | Pops the first element from one of multiple lists. Blocks until an element is available otherwise. Deletes the list if the last element was popped. |
| `LMPOP` | 7.0.0 | -4 | Returns multiple elements from a list after removing them. Deletes the list if the last element was popped. |

### pubsub

| Command | Since | Arity | Summary |
|---------|-------|-------|---------|
| `PUBSUB|SHARDCHANNELS` | 7.0.0 | -2 | Returns the active shard channels. |
| `PUBSUB|SHARDNUMSUB` | 7.0.0 | -2 | Returns the count of subscribers of shard channels. |
| `SPUBLISH` | 7.0.0 | 3 | Post a message to a shard channel |
| `SSUBSCRIBE` | 7.0.0 | -2 | Listens for messages published to shard channels. |
| `SUNSUBSCRIBE` | 7.0.0 | -1 | Stops listening to messages posted to shard channels. |

### scripting

| Command | Since | Arity | Summary |
|---------|-------|-------|---------|
| `EVALSHA_RO` | 7.0.0 | -3 | Executes a read-only server-side Lua script by SHA1 digest. |
| `EVAL_RO` | 7.0.0 | -3 | Executes a read-only server-side Lua script. |
| `FCALL` | 7.0.0 | -3 | Invokes a function. |
| `FCALL_RO` | 7.0.0 | -3 | Invokes a read-only function. |
| `FUNCTION` | 7.0.0 | -2 | A container for function commands. |
| `FUNCTION|DELETE` | 7.0.0 | 3 | Deletes a library and its functions. |
| `FUNCTION|DUMP` | 7.0.0 | 2 | Dumps all libraries into a serialized binary payload. |
| `FUNCTION|FLUSH` | 7.0.0 | -2 | Deletes all libraries and functions. |
| `FUNCTION|HELP` | 7.0.0 | 2 | Returns helpful text about the different subcommands. |
| `FUNCTION|KILL` | 7.0.0 | 2 | Terminates a function during execution. |
| `FUNCTION|LIST` | 7.0.0 | -2 | Returns information about all libraries. |
| `FUNCTION|LOAD` | 7.0.0 | -3 | Creates a library. |
| `FUNCTION|RESTORE` | 7.0.0 | -3 | Restores all libraries from a payload. |
| `FUNCTION|STATS` | 7.0.0 | 2 | Returns information about a function during execution. |

### server

| Command | Since | Arity | Summary |
|---------|-------|-------|---------|
| `ACL|DRYRUN` | 7.0.0 | -4 | Simulates the execution of a command by a user, without executing the command. |
| `COMMAND|DOCS` | 7.0.0 | -2 | Returns documentary information about one, multiple or all commands. |
| `COMMAND|GETKEYSANDFLAGS` | 7.0.0 | -3 | Extracts the key names and access flags for an arbitrary command. |
| `COMMAND|LIST` | 7.0.0 | -2 | Returns a list of command names. |
| `LATENCY|HISTOGRAM` | 7.0.0 | -2 | Returns the cumulative distribution of latencies of a subset or all commands. |
| `MODULE|LOADEX` | 7.0.0 | -3 | Loads a module using extended parameters. |

### set

| Command | Since | Arity | Summary |
|---------|-------|-------|---------|
| `SINTERCARD` | 7.0.0 | -3 | Returns the number of members of the intersect of multiple sets. |

### sorted-set

| Command | Since | Arity | Summary |
|---------|-------|-------|---------|
| `BZMPOP` | 7.0.0 | -5 | Removes and returns a member by score from one or more sorted sets. Blocks until a member is available otherwise. Deletes the sorted set if the last element was popped. |
| `ZINTERCARD` | 7.0.0 | -3 | Returns the number of members of the intersect of multiple sorted sets. |
| `ZMPOP` | 7.0.0 | -4 | Returns the highest- or lowest-scoring members from one or more sorted sets after removing them. Deletes the sorted set if the last member was popped. |

### string

| Command | Since | Arity | Summary |
|---------|-------|-------|---------|
| `LCS` | 7.0.0 | -3 | Finds the longest common substring. |

---
## 2. Removed / Deprecated Commands

| Command | v6 Arity | v6 Flags |
|---------|----------|----------|
| `HOST:` | -1 | LOADING, READONLY, STALE |
| `POST` | -1 | LOADING, READONLY, STALE |
| `STRALGO` | -2 | MOVABLEKEYS, READONLY |

---
## 3. Subcommands in v7

v7 restructured many commands into parent + subcommand form.

### `ACL`

| Subcommand | Since | Arity | Summary |
|------------|-------|-------|---------|
| `ACL|CAT` | 6.0.0 | -2 | Lists the ACL categories, or the commands inside a category. |
| `ACL|DELUSER` | 6.0.0 | -3 | Deletes ACL users, and terminates their connections. |
| `ACL|DRYRUN` | 7.0.0 **NEW** | -4 | Simulates the execution of a command by a user, without executing the command. |
| `ACL|GENPASS` | 6.0.0 | -2 | Generates a pseudorandom, secure password that can be used to identify ACL users. |
| `ACL|GETUSER` | 6.0.0 | 3 | Lists the ACL rules of a user. |
| `ACL|HELP` | 6.0.0 | 2 | Returns helpful text about the different subcommands. |
| `ACL|LIST` | 6.0.0 | 2 | Dumps the effective rules in ACL file format. |
| `ACL|LOAD` | 6.0.0 | 2 | Reloads the rules from the configured ACL file. |
| `ACL|LOG` | 6.0.0 | -2 | Lists recent security events generated due to ACL rules. |
| `ACL|SAVE` | 6.0.0 | 2 | Saves the effective ACL rules in the configured ACL file. |
| `ACL|SETUSER` | 6.0.0 | -3 | Creates and modifies an ACL user and its rules. |
| `ACL|USERS` | 6.0.0 | 2 | Lists all ACL users. |
| `ACL|WHOAMI` | 6.0.0 | 2 | Returns the authenticated username of the current connection. |

### `CLIENT`

| Subcommand | Since | Arity | Summary |
|------------|-------|-------|---------|
| `CLIENT|CACHING` | 6.0.0 | 3 | Instructs the server whether to track the keys in the next request. |
| `CLIENT|GETNAME` | 2.6.9 | 2 | Returns the name of the connection. |
| `CLIENT|GETREDIR` | 6.0.0 | 2 | Returns the client ID to which the connection's tracking notifications are redirected. |
| `CLIENT|HELP` | 5.0.0 | 2 | Returns helpful text about the different subcommands. |
| `CLIENT|ID` | 5.0.0 | 2 | Returns the unique client ID of the connection. |
| `CLIENT|INFO` | 6.2.0 | 2 | Returns information about the connection. |
| `CLIENT|KILL` | 2.4.0 | -3 | Terminates open connections. |
| `CLIENT|LIST` | 2.4.0 | -2 | Lists open connections. |
| `CLIENT|NO-EVICT` | 7.0.0 **NEW** | 3 | Sets the client eviction mode of the connection. |
| `CLIENT|NO-TOUCH` | 7.2.0 **NEW** | 3 | Controls whether commands sent by the client affect the LRU/LFU of accessed keys. |
| `CLIENT|PAUSE` | 3.0.0 | -3 | Suspends commands processing. |
| `CLIENT|REPLY` | 3.2.0 | 3 | Instructs the server whether to reply to commands. |
| `CLIENT|SETINFO` | 7.2.0 **NEW** | 4 | Sets information specific to the client or connection. |
| `CLIENT|SETNAME` | 2.6.9 | 3 | Sets the connection name. |
| `CLIENT|TRACKING` | 6.0.0 | -3 | Controls server-assisted client-side caching for the connection. |
| `CLIENT|TRACKINGINFO` | 6.2.0 | 2 | Returns information about server-assisted client-side caching for the connection. |
| `CLIENT|UNBLOCK` | 5.0.0 | -3 | Unblocks a client blocked by a blocking command from a different connection. |
| `CLIENT|UNPAUSE` | 6.2.0 | 2 | Resumes processing commands from paused clients. |

### `CLUSTER`

| Subcommand | Since | Arity | Summary |
|------------|-------|-------|---------|
| `CLUSTER|ADDSLOTS` | 3.0.0 | -3 | Assigns new hash slots to a node. |
| `CLUSTER|ADDSLOTSRANGE` | 7.0.0 **NEW** | -4 | Assigns new hash slot ranges to a node. |
| `CLUSTER|BUMPEPOCH` | 3.0.0 | 2 | Advances the cluster config epoch. |
| `CLUSTER|COUNT-FAILURE-REPORTS` | 3.0.0 | 3 | Returns the number of active failure reports active for a node. |
| `CLUSTER|COUNTKEYSINSLOT` | 3.0.0 | 3 | Returns the number of keys in a hash slot. |
| `CLUSTER|DELSLOTS` | 3.0.0 | -3 | Sets hash slots as unbound for a node. |
| `CLUSTER|DELSLOTSRANGE` | 7.0.0 **NEW** | -4 | Sets hash slot ranges as unbound for a node. |
| `CLUSTER|FAILOVER` | 3.0.0 | -2 | Forces a replica to perform a manual failover of its master. |
| `CLUSTER|FLUSHSLOTS` | 3.0.0 | 2 | Deletes all slots information from a node. |
| `CLUSTER|FORGET` | 3.0.0 | 3 | Removes a node from the nodes table. |
| `CLUSTER|GETKEYSINSLOT` | 3.0.0 | 4 | Returns the key names in a hash slot. |
| `CLUSTER|HELP` | 5.0.0 | 2 | Returns helpful text about the different subcommands. |
| `CLUSTER|INFO` | 3.0.0 | 2 | Returns information about the state of a node. |
| `CLUSTER|KEYSLOT` | 3.0.0 | 3 | Returns the hash slot for a key. |
| `CLUSTER|LINKS` | 7.0.0 **NEW** | 2 | Returns a list of all TCP links to and from peer nodes. |
| `CLUSTER|MEET` | 3.0.0 | -4 | Forces a node to handshake with another node. |
| `CLUSTER|MYID` | 3.0.0 | 2 | Returns the ID of a node. |
| `CLUSTER|MYSHARDID` | 7.2.0 **NEW** | 2 | Returns the shard ID of a node. |
| `CLUSTER|NODES` | 3.0.0 | 2 | Returns the cluster configuration for a node. |
| `CLUSTER|REPLICAS` | 5.0.0 | 3 | Lists the replica nodes of a master node. |
| `CLUSTER|REPLICATE` | 3.0.0 | 3 | Configure a node as replica of a master node. |
| `CLUSTER|RESET` | 3.0.0 | -2 | Resets a node. |
| `CLUSTER|SAVECONFIG` | 3.0.0 | 2 | Forces a node to save the cluster configuration to disk. |
| `CLUSTER|SET-CONFIG-EPOCH` | 3.0.0 | 3 | Sets the configuration epoch for a new node. |
| `CLUSTER|SETSLOT` | 3.0.0 | -4 | Binds a hash slot to a node. |
| `CLUSTER|SHARDS` | 7.0.0 **NEW** | 2 | Returns the mapping of cluster slots to shards. |
| `CLUSTER|SLAVES` | 3.0.0 | 3 | Lists the replica nodes of a master node. |
| `CLUSTER|SLOTS` | 3.0.0 | 2 | Returns the mapping of cluster slots to nodes. |

### `COMMAND`

| Subcommand | Since | Arity | Summary |
|------------|-------|-------|---------|
| `COMMAND|COUNT` | 2.8.13 | 2 | Returns a count of commands. |
| `COMMAND|DOCS` | 7.0.0 **NEW** | -2 | Returns documentary information about one, multiple or all commands. |
| `COMMAND|GETKEYS` | 2.8.13 | -3 | Extracts the key names from an arbitrary command. |
| `COMMAND|GETKEYSANDFLAGS` | 7.0.0 **NEW** | -3 | Extracts the key names and access flags for an arbitrary command. |
| `COMMAND|HELP` | 5.0.0 | 2 | Returns helpful text about the different subcommands. |
| `COMMAND|INFO` | 2.8.13 | -2 | Returns information about one, multiple or all commands. |
| `COMMAND|LIST` | 7.0.0 **NEW** | -2 | Returns a list of command names. |

### `CONFIG`

| Subcommand | Since | Arity | Summary |
|------------|-------|-------|---------|
| `CONFIG|GET` | 2.0.0 | -3 | Returns the effective values of configuration parameters. |
| `CONFIG|HELP` | 5.0.0 | 2 | Returns helpful text about the different subcommands. |
| `CONFIG|RESETSTAT` | 2.0.0 | 2 | Resets the server's statistics. |
| `CONFIG|REWRITE` | 2.8.0 | 2 | Persists the effective configuration to file. |
| `CONFIG|SET` | 2.0.0 | -4 | Sets configuration parameters in-flight. |

### `FUNCTION`

| Subcommand | Since | Arity | Summary |
|------------|-------|-------|---------|
| `FUNCTION|DELETE` | 7.0.0 **NEW** | 3 | Deletes a library and its functions. |
| `FUNCTION|DUMP` | 7.0.0 **NEW** | 2 | Dumps all libraries into a serialized binary payload. |
| `FUNCTION|FLUSH` | 7.0.0 **NEW** | -2 | Deletes all libraries and functions. |
| `FUNCTION|HELP` | 7.0.0 **NEW** | 2 | Returns helpful text about the different subcommands. |
| `FUNCTION|KILL` | 7.0.0 **NEW** | 2 | Terminates a function during execution. |
| `FUNCTION|LIST` | 7.0.0 **NEW** | -2 | Returns information about all libraries. |
| `FUNCTION|LOAD` | 7.0.0 **NEW** | -3 | Creates a library. |
| `FUNCTION|RESTORE` | 7.0.0 **NEW** | -3 | Restores all libraries from a payload. |
| `FUNCTION|STATS` | 7.0.0 **NEW** | 2 | Returns information about a function during execution. |

### `LATENCY`

| Subcommand | Since | Arity | Summary |
|------------|-------|-------|---------|
| `LATENCY|DOCTOR` | 2.8.13 | 2 | Returns a human-readable latency analysis report. |
| `LATENCY|GRAPH` | 2.8.13 | 3 | Returns a latency graph for an event. |
| `LATENCY|HELP` | 2.8.13 | 2 | Returns helpful text about the different subcommands. |
| `LATENCY|HISTOGRAM` | 7.0.0 **NEW** | -2 | Returns the cumulative distribution of latencies of a subset or all commands. |
| `LATENCY|HISTORY` | 2.8.13 | 3 | Returns timestamp-latency samples for an event. |
| `LATENCY|LATEST` | 2.8.13 | 2 | Returns the latest latency samples for all events. |
| `LATENCY|RESET` | 2.8.13 | -2 | Resets the latency data for one or more events. |

### `MEMORY`

| Subcommand | Since | Arity | Summary |
|------------|-------|-------|---------|
| `MEMORY|DOCTOR` | 4.0.0 | 2 | Outputs a memory problems report. |
| `MEMORY|HELP` | 4.0.0 | 2 | Returns helpful text about the different subcommands. |
| `MEMORY|MALLOC-STATS` | 4.0.0 | 2 | Returns the allocator statistics. |
| `MEMORY|PURGE` | 4.0.0 | 2 | Asks the allocator to release memory. |
| `MEMORY|STATS` | 4.0.0 | 2 | Returns details about memory usage. |
| `MEMORY|USAGE` | 4.0.0 | -3 | Estimates the memory usage of a key. |

### `MODULE`

| Subcommand | Since | Arity | Summary |
|------------|-------|-------|---------|
| `MODULE|HELP` | 5.0.0 | 2 | Returns helpful text about the different subcommands. |
| `MODULE|LIST` | 4.0.0 | 2 | Returns all loaded modules. |
| `MODULE|LOAD` | 4.0.0 | -3 | Loads a module. |
| `MODULE|LOADEX` | 7.0.0 **NEW** | -3 | Loads a module using extended parameters. |
| `MODULE|UNLOAD` | 4.0.0 | 3 | Unloads a module. |

### `OBJECT`

| Subcommand | Since | Arity | Summary |
|------------|-------|-------|---------|
| `OBJECT|ENCODING` | 2.2.3 | 3 | Returns the internal encoding of a Redis object. |
| `OBJECT|FREQ` | 4.0.0 | 3 | Returns the logarithmic access frequency counter of a Redis object. |
| `OBJECT|HELP` | 6.2.0 | 2 | Returns helpful text about the different subcommands. |
| `OBJECT|IDLETIME` | 2.2.3 | 3 | Returns the time since the last access to a Redis object. |
| `OBJECT|REFCOUNT` | 2.2.3 | 3 | Returns the reference count of a value of a key. |

### `PUBSUB`

| Subcommand | Since | Arity | Summary |
|------------|-------|-------|---------|
| `PUBSUB|CHANNELS` | 2.8.0 | -2 | Returns the active channels. |
| `PUBSUB|HELP` | 6.2.0 | 2 | Returns helpful text about the different subcommands. |
| `PUBSUB|NUMPAT` | 2.8.0 | 2 | Returns a count of unique pattern subscriptions. |
| `PUBSUB|NUMSUB` | 2.8.0 | -2 | Returns a count of subscribers to channels. |
| `PUBSUB|SHARDCHANNELS` | 7.0.0 **NEW** | -2 | Returns the active shard channels. |
| `PUBSUB|SHARDNUMSUB` | 7.0.0 **NEW** | -2 | Returns the count of subscribers of shard channels. |

### `SCRIPT`

| Subcommand | Since | Arity | Summary |
|------------|-------|-------|---------|
| `SCRIPT|DEBUG` | 3.2.0 | 3 | Sets the debug mode of server-side Lua scripts. |
| `SCRIPT|EXISTS` | 2.6.0 | -3 | Determines whether server-side Lua scripts exist in the script cache. |
| `SCRIPT|FLUSH` | 2.6.0 | -2 | Removes all server-side Lua scripts from the script cache. |
| `SCRIPT|HELP` | 5.0.0 | 2 | Returns helpful text about the different subcommands. |
| `SCRIPT|KILL` | 2.6.0 | 2 | Terminates a server-side Lua script during execution. |
| `SCRIPT|LOAD` | 2.6.0 | 3 | Loads a server-side Lua script to the script cache. |

### `SLOWLOG`

| Subcommand | Since | Arity | Summary |
|------------|-------|-------|---------|
| `SLOWLOG|GET` | 2.2.12 | -2 | Returns the slow log's entries. |
| `SLOWLOG|HELP` | 6.2.0 | 2 | Show helpful text about the different subcommands |
| `SLOWLOG|LEN` | 2.2.12 | 2 | Returns the number of entries in the slow log. |
| `SLOWLOG|RESET` | 2.2.12 | 2 | Clears all entries from the slow log. |

### `XGROUP`

| Subcommand | Since | Arity | Summary |
|------------|-------|-------|---------|
| `XGROUP|CREATE` | 5.0.0 | -5 | Creates a consumer group. |
| `XGROUP|CREATECONSUMER` | 6.2.0 | 5 | Creates a consumer in a consumer group. |
| `XGROUP|DELCONSUMER` | 5.0.0 | 5 | Deletes a consumer from a consumer group. |
| `XGROUP|DESTROY` | 5.0.0 | 4 | Destroys a consumer group. |
| `XGROUP|HELP` | 5.0.0 | 2 | Returns helpful text about the different subcommands. |
| `XGROUP|SETID` | 5.0.0 | -5 | Sets the last-delivered ID of a consumer group. |

### `XINFO`

| Subcommand | Since | Arity | Summary |
|------------|-------|-------|---------|
| `XINFO|CONSUMERS` | 5.0.0 | 4 | Returns a list of the consumers in a consumer group. |
| `XINFO|GROUPS` | 5.0.0 | 3 | Returns a list of the consumer groups of a stream. |
| `XINFO|HELP` | 5.0.0 | 2 | Returns helpful text about the different subcommands. |
| `XINFO|STREAM` | 5.0.0 | -3 | Returns information about a stream. |

---
## 4. Arity Changes

| Command | v6 | v7 | Notes |
|---------|----|----|-------|
| `EXPIRE` | 3 | -3 | Fixed → variable args |
| `EXPIREAT` | 3 | -3 | Fixed → variable args |
| `PEXPIRE` | 3 | -3 | Fixed → variable args |
| `PEXPIREAT` | 3 | -3 | Fixed → variable args |
| `PFDEBUG` | -3 | 3 | Variable → fixed args |
| `XSETID` | 3 | -3 | Fixed → variable args |
| `ZRANK` | 3 | -3 | Fixed → variable args |
| `ZREVRANK` | 3 | -3 | Fixed → variable args |

---
## 5. Command Flag Changes

| Command | Added | Removed |
|---------|-------|---------|
| `ACL` | — | ADMIN, LOADING, NOSCRIPT, STALE |
| `AUTH` | ALLOW_BUSY | — |
| `BGREWRITEAOF` | NO_ASYNC_LOADING | — |
| `BGSAVE` | NO_ASYNC_LOADING | — |
| `BLMOVE` | BLOCKING | NOSCRIPT |
| `BLPOP` | BLOCKING | NOSCRIPT |
| `BRPOP` | BLOCKING | NOSCRIPT |
| `BRPOPLPUSH` | BLOCKING | NOSCRIPT |
| `BZPOPMAX` | BLOCKING | NOSCRIPT |
| `BZPOPMIN` | BLOCKING | NOSCRIPT |
| `CLIENT` | — | ADMIN, LOADING, NOSCRIPT, RANDOM, STALE |
| `CLUSTER` | — | ADMIN, RANDOM, STALE |
| `COMMAND` | — | RANDOM |
| `CONFIG` | — | ADMIN, LOADING, NOSCRIPT, STALE |
| `DISCARD` | ALLOW_BUSY | — |
| `DUMP` | — | RANDOM |
| `ECHO` | LOADING, STALE | — |
| `EVAL` | NO_MANDATORY_KEYS, STALE | MAY_REPLICATE |
| `EVALSHA` | NO_MANDATORY_KEYS, STALE | MAY_REPLICATE |
| `HELLO` | ALLOW_BUSY | — |
| `HGETALL` | — | RANDOM |
| `HKEYS` | — | TO_SORT |
| `HRANDFIELD` | — | RANDOM |
| `HSCAN` | — | RANDOM |
| `HVALS` | — | TO_SORT |
| `INFO` | — | RANDOM |
| `KEYS` | — | TO_SORT |
| `LASTSAVE` | — | RANDOM |
| `LATENCY` | — | ADMIN, LOADING, NOSCRIPT, STALE |
| `MEMORY` | — | MOVABLEKEYS, RANDOM, READONLY |
| `MIGRATE` | — | RANDOM |
| `MODULE` | — | ADMIN, NOSCRIPT |
| `MULTI` | ALLOW_BUSY | — |
| `OBJECT` | — | RANDOM, READONLY |
| `PFCOUNT` | — | MAY_REPLICATE |
| `PING` | — | STALE |
| `PSYNC` | NO_ASYNC_LOADING, NO_MULTI | — |
| `PTTL` | — | RANDOM |
| `PUBLISH` | — | MAY_REPLICATE |
| `PUBSUB` | — | LOADING, PUBSUB, RANDOM, STALE |
| `RANDOMKEY` | — | RANDOM |
| `READONLY` | LOADING, STALE | — |
| `READWRITE` | LOADING, STALE | — |
| `REPLCONF` | ALLOW_BUSY | — |
| `REPLICAOF` | NO_ASYNC_LOADING | — |
| `RESET` | ALLOW_BUSY, NO_AUTH | — |
| `SAVE` | NO_ASYNC_LOADING, NO_MULTI | — |
| `SCAN` | — | RANDOM |
| `SCRIPT` | — | MAY_REPLICATE, NOSCRIPT |
| `SDIFF` | — | TO_SORT |
| `SHUTDOWN` | ALLOW_BUSY, NO_MULTI | — |
| `SINTER` | — | TO_SORT |
| `SLAVEOF` | NO_ASYNC_LOADING | — |
| `SLOWLOG` | — | ADMIN, LOADING, RANDOM, STALE |
| `SMEMBERS` | — | TO_SORT |
| `SPOP` | — | RANDOM |
| `SRANDMEMBER` | — | RANDOM |
| `SSCAN` | — | RANDOM |
| `SUNION` | — | TO_SORT |
| `SYNC` | NO_ASYNC_LOADING, NO_MULTI | — |
| `TIME` | — | RANDOM |
| `TTL` | — | RANDOM |
| `UNWATCH` | ALLOW_BUSY | — |
| `WAIT` | — | NOSCRIPT |
| `WATCH` | ALLOW_BUSY | — |
| `XACK` | — | RANDOM |
| `XADD` | — | RANDOM |
| `XAUTOCLAIM` | — | RANDOM |
| `XCLAIM` | — | RANDOM |
| `XGROUP` | — | DENYOOM, WRITE |
| `XINFO` | — | RANDOM, READONLY |
| `XPENDING` | — | RANDOM |
| `XREAD` | BLOCKING | — |
| `XREADGROUP` | BLOCKING | — |
| `XTRIM` | — | RANDOM |
| `ZRANDMEMBER` | — | RANDOM |
| `ZSCAN` | — | RANDOM |

---
## 6. ACL Category Changes

| Command | Added | Removed |
|---------|-------|---------|
| `ACL` | — | ADMIN, DANGEROUS |
| `ASKING` | CONNECTION | KEYSPACE |
| `CLIENT` | — | ADMIN, CONNECTION, DANGEROUS |
| `CLUSTER` | — | ADMIN, DANGEROUS |
| `CONFIG` | — | ADMIN, DANGEROUS |
| `LATENCY` | — | ADMIN, DANGEROUS |
| `MEMORY` | — | READ |
| `MODULE` | — | ADMIN, DANGEROUS |
| `OBJECT` | — | KEYSPACE, READ |
| `PUBSUB` | — | PUBSUB |
| `READONLY` | CONNECTION | KEYSPACE |
| `READWRITE` | CONNECTION | KEYSPACE |
| `ROLE` | ADMIN | — |
| `SCRIPT` | — | SCRIPTING |
| `SELECT` | CONNECTION | KEYSPACE |
| `SLOWLOG` | — | ADMIN, DANGEROUS |
| `WAIT` | CONNECTION | KEYSPACE |
| `XGROUP` | — | STREAM, WRITE |
| `XINFO` | — | READ, STREAM |

---
## 7. New v7 Arguments on Existing Commands

Arguments with `since >= 7.0.0` on commands that existed before v7.

### `BITCOUNT`

- *7.0.0*: Added the `BYTE|BIT` option.

New arguments:
  - `unit` (type: oneof) [optional] since 7.0.0

### `BITPOS`

- *7.0.0*: Added the `BYTE|BIT` option.

New arguments:
    - `unit` (type: oneof) [optional] since 7.0.0

### `EXPIRE`

- *7.0.0*: Added options: `NX`, `XX`, `GT` and `LT`.

New arguments:
- `condition` (type: oneof) [optional] since 7.0.0

### `EXPIREAT`

- *7.0.0*: Added options: `NX`, `XX`, `GT` and `LT`.

New arguments:
- `condition` (type: oneof) [optional] since 7.0.0

### `PEXPIRE`

- *7.0.0*: Added options: `NX`, `XX`, `GT` and `LT`.

New arguments:
- `condition` (type: oneof) [optional] since 7.0.0

### `PEXPIREAT`

- *7.0.0*: Added options: `NX`, `XX`, `GT` and `LT`.

New arguments:
- `condition` (type: oneof) [optional] since 7.0.0

### `SHUTDOWN`

- *7.0.0*: Added the `NOW`, `FORCE` and `ABORT` modifiers.

New arguments:
- `now` (type: pure-token) token=`NOW` [optional] since 7.0.0
- `force` (type: pure-token) token=`FORCE` [optional] since 7.0.0
- `abort` (type: pure-token) token=`ABORT` [optional] since 7.0.0

### `XSETID`

- *7.0.0*: Added the `entries_added` and `max_deleted_entry_id` arguments.

New arguments:
- `entries-added` (type: integer) token=`ENTRIESADDED` [optional] since 7.0.0
- `max-deleted-id` (type: string) token=`MAXDELETEDID` [optional] since 7.0.0

---
## 8. Behavioral Changes (from `history` field)

- **`ACL|GETUSER`**
  - 7.0.0: Added selectors and changed the format of key and channel patterns from a list to their rule representation.
- **`ACL|LOG`**
  - 7.2.0: Added entry ID, timestamp created, and timestamp last updated.
- **`ACL|SETUSER`**
  - 7.0.0: Added selectors and key based permissions.
- **`BITCOUNT`**
  - 7.0.0: Added the `BYTE|BIT` option.
- **`BITPOS`**
  - 7.0.0: Added the `BYTE|BIT` option.
- **`CLIENT|LIST`**
  - 7.0.0: Added `resp`, `multi-mem`, `rbs` and `rbp` fields.
  - 7.0.3: Added `ssub` field.
- **`CLUSTER|SLOTS`**
  - 7.0.0: Added additional networking metadata field.
- **`COMMAND|INFO`**
  - 7.0.0: Allowed to be called with no argument to get info on all commands.
- **`CONFIG|GET`**
  - 7.0.0: Added the ability to pass multiple pattern parameters in one call
- **`CONFIG|SET`**
  - 7.0.0: Added the ability to set multiple parameters in one call.
- **`EXPIRE`**
  - 7.0.0: Added options: `NX`, `XX`, `GT` and `LT`.
- **`EXPIREAT`**
  - 7.0.0: Added options: `NX`, `XX`, `GT` and `LT`.
- **`GEORADIUS`**
  - 7.0.0: Added support for uppercase unit names.
- **`GEORADIUSBYMEMBER`**
  - 7.0.0: Added support for uppercase unit names.
- **`GEOSEARCH`**
  - 7.0.0: Added support for uppercase unit names.
- **`GEOSEARCHSTORE`**
  - 7.0.0: Added support for uppercase unit names.
- **`INFO`**
  - 7.0.0: Added support for taking multiple section arguments.
- **`PEXPIRE`**
  - 7.0.0: Added options: `NX`, `XX`, `GT` and `LT`.
- **`PEXPIREAT`**
  - 7.0.0: Added options: `NX`, `XX`, `GT` and `LT`.
- **`SET`**
  - 7.0.0: Allowed the `NX` and `GET` options to be used together.
- **`SHUTDOWN`**
  - 7.0.0: Added the `NOW`, `FORCE` and `ABORT` modifiers.
- **`XADD`**
  - 7.0.0: Added support for the `<ms>-*` explicit ID form.
- **`XAUTOCLAIM`**
  - 7.0.0: Added an element to the reply array, containing deleted entries the command cleared from the PEL
- **`XGROUP|CREATE`**
  - 7.0.0: Added the `entries_read` named argument.
- **`XGROUP|SETID`**
  - 7.0.0: Added the optional `entries_read` argument.
- **`XINFO|CONSUMERS`**
  - 7.2.0: Added the `inactive` field.
- **`XINFO|GROUPS`**
  - 7.0.0: Added the `entries-read` and `lag` fields
- **`XINFO|STREAM`**
  - 7.0.0: Added the `max-deleted-entry-id`, `entries-added`, `recorded-first-entry-id`, `entries-read` and `lag` fields
  - 7.2.0: Added the `active-time` field, and changed the meaning of `seen-time`.
- **`XSETID`**
  - 7.0.0: Added the `entries_added` and `max_deleted_entry_id` arguments.
- **`ZRANK`**
  - 7.2.0: Added the optional `WITHSCORE` argument.
- **`ZREVRANK`**
  - 7.2.0: Added the optional `WITHSCORE` argument.

---
## 9. Input Parameter (Argument) Differences

Deep comparison of argument structure for commands present in both v6 and v7.

### `BITCOUNT`

- **~** `range` sub-arguments:
  - **+** `unit` (type: oneof) [optional] since 7.0.0

### `BITPOS`

- **~** `range` sub-arguments:
  - **~** `end-unit-block` sub-arguments:
    - **+** `unit` (type: oneof) [optional] since 7.0.0

### `EXPIRE`

- **+** `condition` (type: oneof) [optional] since 7.0.0

### `EXPIREAT`

- **+** `condition` (type: oneof) [optional] since 7.0.0

### `PEXPIRE`

- **+** `condition` (type: oneof) [optional] since 7.0.0

### `PEXPIREAT`

- **+** `condition` (type: oneof) [optional] since 7.0.0

### `SHUTDOWN`

- **+** `now` (type: pure-token) token=`NOW` [optional] since 7.0.0
- **+** `force` (type: pure-token) token=`FORCE` [optional] since 7.0.0
- **+** `abort` (type: pure-token) token=`ABORT` [optional] since 7.0.0

### `XSETID`

- **+** `entries-added` (type: integer) token=`ENTRIESADDED` [optional] since 7.0.0
- **+** `max-deleted-id` (type: string) token=`MAXDELETEDID` [optional] since 7.0.0

---
## 10. Reply Schema (Output) Differences

Comparison of `reply_schema` between v6 and v7 for shared commands.

*No reply schema differences found.*

---
## 11. Deprecated Commands in v7

| Command | Deprecated Since | Replaced By |
|---------|-----------------|-------------|
| `BRPOPLPUSH` | 6.2.0 | `BLMOVE` with the `RIGHT` and `LEFT` arguments |
| `CLUSTER|SLAVES` | 5.0.0 | `CLUSTER REPLICAS` |
| `CLUSTER|SLOTS` | 7.0.0 | `CLUSTER SHARDS` |
| `DEBUG` |  |  |
| `GEORADIUS` | 6.2.0 | `GEOSEARCH` and `GEOSEARCHSTORE` with the `BYRADIUS` argument |
| `GEORADIUSBYMEMBER` | 6.2.0 | `GEOSEARCH` and `GEOSEARCHSTORE` with the `BYRADIUS` and `FROMMEMBER` arguments |
| `GEORADIUSBYMEMBER_RO` | 6.2.0 | `GEOSEARCH` with the `BYRADIUS` and `FROMMEMBER` arguments |
| `GEORADIUS_RO` | 6.2.0 | `GEOSEARCH` with the `BYRADIUS` argument |
| `GETSET` | 6.2.0 | `SET` with the `!GET` argument |
| `HMSET` | 4.0.0 | `HSET` with multiple field-value pairs |
| `PFDEBUG` |  |  |
| `PFSELFTEST` |  |  |
| `PSETEX` | 2.6.12 | `SET` with the `PX` argument |
| `QUIT` | 7.2.0 | just closing the connection |
| `REPLCONF` |  |  |
| `RESTORE-ASKING` |  |  |
| `RPOPLPUSH` | 6.2.0 | `LMOVE` with the `RIGHT` and `LEFT` arguments |
| `SETEX` | 2.6.12 | `SET` with the `EX` argument |
| `SETNX` | 2.6.12 | `SET` with the `NX` argument |
| `SLAVEOF` | 5.0.0 | `REPLICAOF` |
| `SUBSTR` | 2.0.0 | `GETRANGE` |
| `ZRANGEBYLEX` | 6.2.0 | `ZRANGE` with the `BYLEX` argument |
| `ZRANGEBYSCORE` | 6.2.0 | `ZRANGE` with the `BYSCORE` argument |
| `ZREVRANGE` | 6.2.0 | `ZRANGE` with the `REV` argument |
| `ZREVRANGEBYLEX` | 6.2.0 | `ZRANGE` with the `REV` and `BYLEX` arguments |
| `ZREVRANGEBYSCORE` | 6.2.0 | `ZRANGE` with the `REV` and `BYSCORE` arguments |

---
## 12. Full Argument Specs for Shared Commands

<details><summary>Click to expand</summary>

### `ACL|CAT`

v6 arity: `-2` → v7 arity: `-2`  
Group: server | Since: 6.0.0  
Summary: Lists the ACL categories, or the commands inside a category.

Arguments:
- `category` (type: string) [optional]

### `ACL|DELUSER`

v6 arity: `-3` → v7 arity: `-3`  
Group: server | Since: 6.0.0  
Summary: Deletes ACL users, and terminates their connections.

Arguments:
- `username` (type: string) [multiple]

### `ACL|GENPASS`

v6 arity: `-2` → v7 arity: `-2`  
Group: server | Since: 6.0.0  
Summary: Generates a pseudorandom, secure password that can be used to identify ACL users.

Arguments:
- `bits` (type: integer) [optional]

### `ACL|GETUSER`

v6 arity: `3` → v7 arity: `3`  
Group: server | Since: 6.0.0  
Summary: Lists the ACL rules of a user.

Arguments:
- `username` (type: string)

### `ACL|LOG`

v6 arity: `-2` → v7 arity: `-2`  
Group: server | Since: 6.0.0  
Summary: Lists recent security events generated due to ACL rules.

Arguments:
- `operation` (type: oneof) [optional]
  - `count` (type: integer)
  - `reset` (type: pure-token) token=`RESET`

### `ACL|SETUSER`

v6 arity: `-3` → v7 arity: `-3`  
Group: server | Since: 6.0.0  
Summary: Creates and modifies an ACL user and its rules.

Arguments:
- `username` (type: string)
- `rule` (type: string) [optional] [multiple]

### `APPEND`

v6 arity: `3` → v7 arity: `3`  
Group: string | Since: 2.0.0  
Summary: Appends a string to the value of a key. Creates the key if it doesn't exist.

Arguments:
- `key` (type: key)
- `value` (type: string)

### `AUTH`

v6 arity: `-2` → v7 arity: `-2`  
Group: connection | Since: 1.0.0  
Summary: Authenticates the connection.

Arguments:
- `username` (type: string) [optional] since 6.0.0
- `password` (type: string)

### `BGSAVE`

v6 arity: `-1` → v7 arity: `-1`  
Group: server | Since: 1.0.0  
Summary: Asynchronously saves the database(s) to disk.

Arguments:
- `schedule` (type: pure-token) token=`SCHEDULE` [optional] since 3.2.2

### `BITCOUNT`

v6 arity: `-2` → v7 arity: `-2`  
Group: bitmap | Since: 2.6.0  
Summary: Counts the number of set bits (population counting) in a string.

Arguments:
- `key` (type: key)
- `range` (type: block) [optional]
  - `start` (type: integer)
  - `end` (type: integer)
  - `unit` (type: oneof) [optional] since 7.0.0
    - `byte` (type: pure-token) token=`BYTE`
    - `bit` (type: pure-token) token=`BIT`

### `BITFIELD`

v6 arity: `-2` → v7 arity: `-2`  
Group: bitmap | Since: 3.2.0  
Summary: Performs arbitrary bitfield integer operations on strings.

Arguments:
- `key` (type: key)
- `operation` (type: oneof) [optional] [multiple]
  - `get-block` (type: block) token=`GET`
    - `encoding` (type: string)
    - `offset` (type: integer)
  - `write` (type: block)
    - `overflow-block` (type: oneof) token=`OVERFLOW` [optional]
      - `wrap` (type: pure-token) token=`WRAP`
      - `sat` (type: pure-token) token=`SAT`
      - `fail` (type: pure-token) token=`FAIL`
    - `write-operation` (type: oneof)
      - `set-block` (type: block) token=`SET`
        - `encoding` (type: string)
        - `offset` (type: integer)
        - `value` (type: integer)
      - `incrby-block` (type: block) token=`INCRBY`
        - `encoding` (type: string)
        - `offset` (type: integer)
        - `increment` (type: integer)

### `BITFIELD_RO`

v6 arity: `-2` → v7 arity: `-2`  
Group: bitmap | Since: 6.0.0  
Summary: Performs arbitrary read-only bitfield integer operations on strings.

Arguments:
- `key` (type: key)
- `get-block` (type: block) token=`GET` [optional] [multiple]
  - `encoding` (type: string)
  - `offset` (type: integer)

### `BITOP`

v6 arity: `-4` → v7 arity: `-4`  
Group: bitmap | Since: 2.6.0  
Summary: Performs bitwise operations on multiple strings, and stores the result.

Arguments:
- `operation` (type: oneof)
  - `and` (type: pure-token) token=`AND`
  - `or` (type: pure-token) token=`OR`
  - `xor` (type: pure-token) token=`XOR`
  - `not` (type: pure-token) token=`NOT`
- `destkey` (type: key)
- `key` (type: key) [multiple]

### `BITPOS`

v6 arity: `-3` → v7 arity: `-3`  
Group: bitmap | Since: 2.8.7  
Summary: Finds the first set (1) or clear (0) bit in a string.

Arguments:
- `key` (type: key)
- `bit` (type: integer)
- `range` (type: block) [optional]
  - `start` (type: integer)
  - `end-unit-block` (type: block) [optional]
    - `end` (type: integer)
    - `unit` (type: oneof) [optional] since 7.0.0
      - `byte` (type: pure-token) token=`BYTE`
      - `bit` (type: pure-token) token=`BIT`

### `BLMOVE`

v6 arity: `6` → v7 arity: `6`  
Group: list | Since: 6.2.0  
Summary: Pops an element from a list, pushes it to another list and returns it. Blocks until an element is available otherwise. Deletes the list if the last element was moved.

Arguments:
- `source` (type: key)
- `destination` (type: key)
- `wherefrom` (type: oneof)
  - `left` (type: pure-token) token=`LEFT`
  - `right` (type: pure-token) token=`RIGHT`
- `whereto` (type: oneof)
  - `left` (type: pure-token) token=`LEFT`
  - `right` (type: pure-token) token=`RIGHT`
- `timeout` (type: double)

### `BLPOP`

v6 arity: `-3` → v7 arity: `-3`  
Group: list | Since: 2.0.0  
Summary: Removes and returns the first element in a list. Blocks until an element is available otherwise. Deletes the list if the last element was popped.

Arguments:
- `key` (type: key) [multiple]
- `timeout` (type: double)

### `BRPOP`

v6 arity: `-3` → v7 arity: `-3`  
Group: list | Since: 2.0.0  
Summary: Removes and returns the last element in a list. Blocks until an element is available otherwise. Deletes the list if the last element was popped.

Arguments:
- `key` (type: key) [multiple]
- `timeout` (type: double)

### `BRPOPLPUSH`

v6 arity: `4` → v7 arity: `4`  
Group: list | Since: 2.2.0  
Summary: Pops an element from a list, pushes it to another list and returns it. Block until an element is available otherwise. Deletes the list if the last element was popped.

Arguments:
- `source` (type: key)
- `destination` (type: key)
- `timeout` (type: double)

### `BZPOPMAX`

v6 arity: `-3` → v7 arity: `-3`  
Group: sorted-set | Since: 5.0.0  
Summary: Removes and returns the member with the highest score from one or more sorted sets. Blocks until a member available otherwise.  Deletes the sorted set if the last element was popped.

Arguments:
- `key` (type: key) [multiple]
- `timeout` (type: double)

### `BZPOPMIN`

v6 arity: `-3` → v7 arity: `-3`  
Group: sorted-set | Since: 5.0.0  
Summary: Removes and returns the member with the lowest score from one or more sorted sets. Blocks until a member is available otherwise. Deletes the sorted set if the last element was popped.

Arguments:
- `key` (type: key) [multiple]
- `timeout` (type: double)

### `CLIENT|CACHING`

v6 arity: `3` → v7 arity: `3`  
Group: connection | Since: 6.0.0  
Summary: Instructs the server whether to track the keys in the next request.

Arguments:
- `mode` (type: oneof)
  - `yes` (type: pure-token) token=`YES`
  - `no` (type: pure-token) token=`NO`

### `CLIENT|KILL`

v6 arity: `-3` → v7 arity: `-3`  
Group: connection | Since: 2.4.0  
Summary: Terminates open connections.

Arguments:
- `filter` (type: oneof)
  - `old-format` (type: string)
  - `new-format` (type: oneof) [multiple]
    - `client-id` (type: integer) token=`ID` [optional] since 2.8.12
    - `client-type` (type: oneof) token=`TYPE` [optional] since 2.8.12
      - `normal` (type: pure-token) token=`NORMAL`
      - `master` (type: pure-token) token=`MASTER` since 3.2.0
      - `slave` (type: pure-token) token=`SLAVE`
      - `replica` (type: pure-token) token=`REPLICA` since 5.0.0
      - `pubsub` (type: pure-token) token=`PUBSUB`
    - `username` (type: string) token=`USER` [optional]
    - `addr` (type: string) token=`ADDR` [optional]
    - `laddr` (type: string) token=`LADDR` [optional] since 6.2.0
    - `skipme` (type: oneof) token=`SKIPME` [optional]
      - `yes` (type: pure-token) token=`YES`
      - `no` (type: pure-token) token=`NO`

### `CLIENT|LIST`

v6 arity: `-2` → v7 arity: `-2`  
Group: connection | Since: 2.4.0  
Summary: Lists open connections.

Arguments:
- `client-type` (type: oneof) token=`TYPE` [optional] since 5.0.0
  - `normal` (type: pure-token) token=`NORMAL`
  - `master` (type: pure-token) token=`MASTER`
  - `replica` (type: pure-token) token=`REPLICA`
  - `pubsub` (type: pure-token) token=`PUBSUB`
- `client-id` (type: integer) token=`ID` [optional] [multiple] since 6.2.0

### `CLIENT|PAUSE`

v6 arity: `-3` → v7 arity: `-3`  
Group: connection | Since: 3.0.0  
Summary: Suspends commands processing.

Arguments:
- `timeout` (type: integer)
- `mode` (type: oneof) [optional] since 6.2.0
  - `write` (type: pure-token) token=`WRITE`
  - `all` (type: pure-token) token=`ALL`

### `CLIENT|REPLY`

v6 arity: `3` → v7 arity: `3`  
Group: connection | Since: 3.2.0  
Summary: Instructs the server whether to reply to commands.

Arguments:
- `action` (type: oneof)
  - `on` (type: pure-token) token=`ON`
  - `off` (type: pure-token) token=`OFF`
  - `skip` (type: pure-token) token=`SKIP`

### `CLIENT|SETNAME`

v6 arity: `3` → v7 arity: `3`  
Group: connection | Since: 2.6.9  
Summary: Sets the connection name.

Arguments:
- `connection-name` (type: string)

### `CLIENT|TRACKING`

v6 arity: `-3` → v7 arity: `-3`  
Group: connection | Since: 6.0.0  
Summary: Controls server-assisted client-side caching for the connection.

Arguments:
- `status` (type: oneof)
  - `on` (type: pure-token) token=`ON`
  - `off` (type: pure-token) token=`OFF`
- `client-id` (type: integer) token=`REDIRECT` [optional]
- `prefix` (type: string) token=`PREFIX` [optional] [multiple]
- `bcast` (type: pure-token) token=`BCAST` [optional]
- `optin` (type: pure-token) token=`OPTIN` [optional]
- `optout` (type: pure-token) token=`OPTOUT` [optional]
- `noloop` (type: pure-token) token=`NOLOOP` [optional]

### `CLIENT|UNBLOCK`

v6 arity: `-3` → v7 arity: `-3`  
Group: connection | Since: 5.0.0  
Summary: Unblocks a client blocked by a blocking command from a different connection.

Arguments:
- `client-id` (type: integer)
- `unblock-type` (type: oneof) [optional]
  - `timeout` (type: pure-token) token=`TIMEOUT`
  - `error` (type: pure-token) token=`ERROR`

### `CLUSTER|ADDSLOTS`

v6 arity: `-3` → v7 arity: `-3`  
Group: cluster | Since: 3.0.0  
Summary: Assigns new hash slots to a node.

Arguments:
- `slot` (type: integer) [multiple]

### `CLUSTER|COUNT-FAILURE-REPORTS`

v6 arity: `3` → v7 arity: `3`  
Group: cluster | Since: 3.0.0  
Summary: Returns the number of active failure reports active for a node.

Arguments:
- `node-id` (type: string)

### `CLUSTER|COUNTKEYSINSLOT`

v6 arity: `3` → v7 arity: `3`  
Group: cluster | Since: 3.0.0  
Summary: Returns the number of keys in a hash slot.

Arguments:
- `slot` (type: integer)

### `CLUSTER|DELSLOTS`

v6 arity: `-3` → v7 arity: `-3`  
Group: cluster | Since: 3.0.0  
Summary: Sets hash slots as unbound for a node.

Arguments:
- `slot` (type: integer) [multiple]

### `CLUSTER|FAILOVER`

v6 arity: `-2` → v7 arity: `-2`  
Group: cluster | Since: 3.0.0  
Summary: Forces a replica to perform a manual failover of its master.

Arguments:
- `options` (type: oneof) [optional]
  - `force` (type: pure-token) token=`FORCE`
  - `takeover` (type: pure-token) token=`TAKEOVER`

### `CLUSTER|FORGET`

v6 arity: `3` → v7 arity: `3`  
Group: cluster | Since: 3.0.0  
Summary: Removes a node from the nodes table.

Arguments:
- `node-id` (type: string)

### `CLUSTER|GETKEYSINSLOT`

v6 arity: `4` → v7 arity: `4`  
Group: cluster | Since: 3.0.0  
Summary: Returns the key names in a hash slot.

Arguments:
- `slot` (type: integer)
- `count` (type: integer)

### `CLUSTER|KEYSLOT`

v6 arity: `3` → v7 arity: `3`  
Group: cluster | Since: 3.0.0  
Summary: Returns the hash slot for a key.

Arguments:
- `key` (type: string)

### `CLUSTER|MEET`

v6 arity: `-4` → v7 arity: `-4`  
Group: cluster | Since: 3.0.0  
Summary: Forces a node to handshake with another node.

Arguments:
- `ip` (type: string)
- `port` (type: integer)
- `cluster-bus-port` (type: integer) [optional] since 4.0.0

### `CLUSTER|REPLICAS`

v6 arity: `3` → v7 arity: `3`  
Group: cluster | Since: 5.0.0  
Summary: Lists the replica nodes of a master node.

Arguments:
- `node-id` (type: string)

### `CLUSTER|REPLICATE`

v6 arity: `3` → v7 arity: `3`  
Group: cluster | Since: 3.0.0  
Summary: Configure a node as replica of a master node.

Arguments:
- `node-id` (type: string)

### `CLUSTER|RESET`

v6 arity: `-2` → v7 arity: `-2`  
Group: cluster | Since: 3.0.0  
Summary: Resets a node.

Arguments:
- `reset-type` (type: oneof) [optional]
  - `hard` (type: pure-token) token=`HARD`
  - `soft` (type: pure-token) token=`SOFT`

### `CLUSTER|SET-CONFIG-EPOCH`

v6 arity: `3` → v7 arity: `3`  
Group: cluster | Since: 3.0.0  
Summary: Sets the configuration epoch for a new node.

Arguments:
- `config-epoch` (type: integer)

### `CLUSTER|SETSLOT`

v6 arity: `-4` → v7 arity: `-4`  
Group: cluster | Since: 3.0.0  
Summary: Binds a hash slot to a node.

Arguments:
- `slot` (type: integer)
- `subcommand` (type: oneof)
  - `importing` (type: string) token=`IMPORTING`
  - `migrating` (type: string) token=`MIGRATING`
  - `node` (type: string) token=`NODE`
  - `stable` (type: pure-token) token=`STABLE`

### `CLUSTER|SLAVES`

v6 arity: `3` → v7 arity: `3`  
Group: cluster | Since: 3.0.0  
Summary: Lists the replica nodes of a master node.

Arguments:
- `node-id` (type: string)

### `COMMAND|GETKEYS`

v6 arity: `-3` → v7 arity: `-3`  
Group: server | Since: 2.8.13  
Summary: Extracts the key names from an arbitrary command.

Arguments:
- `command` (type: string)
- `arg` (type: string) [optional] [multiple]

### `COMMAND|INFO`

v6 arity: `-2` → v7 arity: `-2`  
Group: server | Since: 2.8.13  
Summary: Returns information about one, multiple or all commands.

Arguments:
- `command-name` (type: string) [optional] [multiple]

### `CONFIG|GET`

v6 arity: `-3` → v7 arity: `-3`  
Group: server | Since: 2.0.0  
Summary: Returns the effective values of configuration parameters.

Arguments:
- `parameter` (type: string) [multiple]

### `CONFIG|SET`

v6 arity: `-4` → v7 arity: `-4`  
Group: server | Since: 2.0.0  
Summary: Sets configuration parameters in-flight.

Arguments:
- `data` (type: block) [multiple]
  - `parameter` (type: string)
  - `value` (type: string)

### `COPY`

v6 arity: `-3` → v7 arity: `-3`  
Group: generic | Since: 6.2.0  
Summary: Copies the value of a key to a new key.

Arguments:
- `source` (type: key)
- `destination` (type: key)
- `destination-db` (type: integer) token=`DB` [optional]
- `replace` (type: pure-token) token=`REPLACE` [optional]

### `DECR`

v6 arity: `2` → v7 arity: `2`  
Group: string | Since: 1.0.0  
Summary: Decrements the integer value of a key by one. Uses 0 as initial value if the key doesn't exist.

Arguments:
- `key` (type: key)

### `DECRBY`

v6 arity: `3` → v7 arity: `3`  
Group: string | Since: 1.0.0  
Summary: Decrements a number from the integer value of a key. Uses 0 as initial value if the key doesn't exist.

Arguments:
- `key` (type: key)
- `decrement` (type: integer)

### `DEL`

v6 arity: `-2` → v7 arity: `-2`  
Group: generic | Since: 1.0.0  
Summary: Deletes one or more keys.

Arguments:
- `key` (type: key) [multiple]

### `DUMP`

v6 arity: `2` → v7 arity: `2`  
Group: generic | Since: 2.6.0  
Summary: Returns a serialized representation of the value stored at a key.

Arguments:
- `key` (type: key)

### `ECHO`

v6 arity: `2` → v7 arity: `2`  
Group: connection | Since: 1.0.0  
Summary: Returns the given string.

Arguments:
- `message` (type: string)

### `EVAL`

v6 arity: `-3` → v7 arity: `-3`  
Group: scripting | Since: 2.6.0  
Summary: Executes a server-side Lua script.

Arguments:
- `script` (type: string)
- `numkeys` (type: integer)
- `key` (type: key) [optional] [multiple]
- `arg` (type: string) [optional] [multiple]

### `EVALSHA`

v6 arity: `-3` → v7 arity: `-3`  
Group: scripting | Since: 2.6.0  
Summary: Executes a server-side Lua script by SHA1 digest.

Arguments:
- `sha1` (type: string)
- `numkeys` (type: integer)
- `key` (type: key) [optional] [multiple]
- `arg` (type: string) [optional] [multiple]

### `EXISTS`

v6 arity: `-2` → v7 arity: `-2`  
Group: generic | Since: 1.0.0  
Summary: Determines whether one or more keys exist.

Arguments:
- `key` (type: key) [multiple]

### `EXPIRE`

v6 arity: `3` → v7 arity: `-3`  
Group: generic | Since: 1.0.0  
Summary: Sets the expiration time of a key in seconds.

Arguments:
- `key` (type: key)
- `seconds` (type: integer)
- `condition` (type: oneof) [optional] since 7.0.0
  - `nx` (type: pure-token) token=`NX`
  - `xx` (type: pure-token) token=`XX`
  - `gt` (type: pure-token) token=`GT`
  - `lt` (type: pure-token) token=`LT`

### `EXPIREAT`

v6 arity: `3` → v7 arity: `-3`  
Group: generic | Since: 1.2.0  
Summary: Sets the expiration time of a key to a Unix timestamp.

Arguments:
- `key` (type: key)
- `unix-time-seconds` (type: unix-time)
- `condition` (type: oneof) [optional] since 7.0.0
  - `nx` (type: pure-token) token=`NX`
  - `xx` (type: pure-token) token=`XX`
  - `gt` (type: pure-token) token=`GT`
  - `lt` (type: pure-token) token=`LT`

### `FAILOVER`

v6 arity: `-1` → v7 arity: `-1`  
Group: server | Since: 6.2.0  
Summary: Starts a coordinated failover from a server to one of its replicas.

Arguments:
- `target` (type: block) token=`TO` [optional]
  - `host` (type: string)
  - `port` (type: integer)
  - `force` (type: pure-token) token=`FORCE` [optional]
- `abort` (type: pure-token) token=`ABORT` [optional]
- `milliseconds` (type: integer) token=`TIMEOUT` [optional]

### `FLUSHALL`

v6 arity: `-1` → v7 arity: `-1`  
Group: server | Since: 1.0.0  
Summary: Removes all keys from all databases.

Arguments:
- `flush-type` (type: oneof) [optional]
  - `async` (type: pure-token) token=`ASYNC` since 4.0.0
  - `sync` (type: pure-token) token=`SYNC` since 6.2.0

### `FLUSHDB`

v6 arity: `-1` → v7 arity: `-1`  
Group: server | Since: 1.0.0  
Summary: Remove all keys from the current database.

Arguments:
- `flush-type` (type: oneof) [optional]
  - `async` (type: pure-token) token=`ASYNC` since 4.0.0
  - `sync` (type: pure-token) token=`SYNC` since 6.2.0

### `GEOADD`

v6 arity: `-5` → v7 arity: `-5`  
Group: geo | Since: 3.2.0  
Summary: Adds one or more members to a geospatial index. The key is created if it doesn't exist.

Arguments:
- `key` (type: key)
- `condition` (type: oneof) [optional] since 6.2.0
  - `nx` (type: pure-token) token=`NX`
  - `xx` (type: pure-token) token=`XX`
- `change` (type: pure-token) token=`CH` [optional] since 6.2.0
- `data` (type: block) [multiple]
  - `longitude` (type: double)
  - `latitude` (type: double)
  - `member` (type: string)

### `GEODIST`

v6 arity: `-4` → v7 arity: `-4`  
Group: geo | Since: 3.2.0  
Summary: Returns the distance between two members of a geospatial index.

Arguments:
- `key` (type: key)
- `member1` (type: string)
- `member2` (type: string)
- `unit` (type: oneof) [optional]
  - `m` (type: pure-token) token=`M`
  - `km` (type: pure-token) token=`KM`
  - `ft` (type: pure-token) token=`FT`
  - `mi` (type: pure-token) token=`MI`

### `GEOHASH`

v6 arity: `-2` → v7 arity: `-2`  
Group: geo | Since: 3.2.0  
Summary: Returns members from a geospatial index as geohash strings.

Arguments:
- `key` (type: key)
- `member` (type: string) [optional] [multiple]

### `GEOPOS`

v6 arity: `-2` → v7 arity: `-2`  
Group: geo | Since: 3.2.0  
Summary: Returns the longitude and latitude of members from a geospatial index.

Arguments:
- `key` (type: key)
- `member` (type: string) [optional] [multiple]

### `GEORADIUS`

v6 arity: `-6` → v7 arity: `-6`  
Group: geo | Since: 3.2.0  
Summary: Queries a geospatial index for members within a distance from a coordinate, optionally stores the result.

Arguments:
- `key` (type: key)
- `longitude` (type: double)
- `latitude` (type: double)
- `radius` (type: double)
- `unit` (type: oneof)
  - `m` (type: pure-token) token=`M`
  - `km` (type: pure-token) token=`KM`
  - `ft` (type: pure-token) token=`FT`
  - `mi` (type: pure-token) token=`MI`
- `withcoord` (type: pure-token) token=`WITHCOORD` [optional]
- `withdist` (type: pure-token) token=`WITHDIST` [optional]
- `withhash` (type: pure-token) token=`WITHHASH` [optional]
- `count-block` (type: block) [optional]
  - `count` (type: integer) token=`COUNT`
  - `any` (type: pure-token) token=`ANY` [optional] since 6.2.0
- `order` (type: oneof) [optional]
  - `asc` (type: pure-token) token=`ASC`
  - `desc` (type: pure-token) token=`DESC`
- `store` (type: oneof) [optional]
  - `storekey` (type: key) token=`STORE`
  - `storedistkey` (type: key) token=`STOREDIST`

### `GEORADIUSBYMEMBER`

v6 arity: `-5` → v7 arity: `-5`  
Group: geo | Since: 3.2.0  
Summary: Queries a geospatial index for members within a distance from a member, optionally stores the result.

Arguments:
- `key` (type: key)
- `member` (type: string)
- `radius` (type: double)
- `unit` (type: oneof)
  - `m` (type: pure-token) token=`M`
  - `km` (type: pure-token) token=`KM`
  - `ft` (type: pure-token) token=`FT`
  - `mi` (type: pure-token) token=`MI`
- `withcoord` (type: pure-token) token=`WITHCOORD` [optional]
- `withdist` (type: pure-token) token=`WITHDIST` [optional]
- `withhash` (type: pure-token) token=`WITHHASH` [optional]
- `count-block` (type: block) [optional]
  - `count` (type: integer) token=`COUNT`
  - `any` (type: pure-token) token=`ANY` [optional]
- `order` (type: oneof) [optional]
  - `asc` (type: pure-token) token=`ASC`
  - `desc` (type: pure-token) token=`DESC`
- `store` (type: oneof) [optional]
  - `storekey` (type: key) token=`STORE`
  - `storedistkey` (type: key) token=`STOREDIST`

### `GEORADIUSBYMEMBER_RO`

v6 arity: `-5` → v7 arity: `-5`  
Group: geo | Since: 3.2.10  
Summary: Returns members from a geospatial index that are within a distance from a member.

Arguments:
- `key` (type: key)
- `member` (type: string)
- `radius` (type: double)
- `unit` (type: oneof)
  - `m` (type: pure-token) token=`M`
  - `km` (type: pure-token) token=`KM`
  - `ft` (type: pure-token) token=`FT`
  - `mi` (type: pure-token) token=`MI`
- `withcoord` (type: pure-token) token=`WITHCOORD` [optional]
- `withdist` (type: pure-token) token=`WITHDIST` [optional]
- `withhash` (type: pure-token) token=`WITHHASH` [optional]
- `count-block` (type: block) [optional]
  - `count` (type: integer) token=`COUNT`
  - `any` (type: pure-token) token=`ANY` [optional]
- `order` (type: oneof) [optional]
  - `asc` (type: pure-token) token=`ASC`
  - `desc` (type: pure-token) token=`DESC`

### `GEORADIUS_RO`

v6 arity: `-6` → v7 arity: `-6`  
Group: geo | Since: 3.2.10  
Summary: Returns members from a geospatial index that are within a distance from a coordinate.

Arguments:
- `key` (type: key)
- `longitude` (type: double)
- `latitude` (type: double)
- `radius` (type: double)
- `unit` (type: oneof)
  - `m` (type: pure-token) token=`M`
  - `km` (type: pure-token) token=`KM`
  - `ft` (type: pure-token) token=`FT`
  - `mi` (type: pure-token) token=`MI`
- `withcoord` (type: pure-token) token=`WITHCOORD` [optional]
- `withdist` (type: pure-token) token=`WITHDIST` [optional]
- `withhash` (type: pure-token) token=`WITHHASH` [optional]
- `count-block` (type: block) [optional]
  - `count` (type: integer) token=`COUNT`
  - `any` (type: pure-token) token=`ANY` [optional] since 6.2.0
- `order` (type: oneof) [optional]
  - `asc` (type: pure-token) token=`ASC`
  - `desc` (type: pure-token) token=`DESC`

### `GEOSEARCH`

v6 arity: `-7` → v7 arity: `-7`  
Group: geo | Since: 6.2.0  
Summary: Queries a geospatial index for members inside an area of a box or a circle.

Arguments:
- `key` (type: key)
- `from` (type: oneof)
  - `member` (type: string) token=`FROMMEMBER`
  - `fromlonlat` (type: block) token=`FROMLONLAT`
    - `longitude` (type: double)
    - `latitude` (type: double)
- `by` (type: oneof)
  - `circle` (type: block)
    - `radius` (type: double) token=`BYRADIUS`
    - `unit` (type: oneof)
      - `m` (type: pure-token) token=`M`
      - `km` (type: pure-token) token=`KM`
      - `ft` (type: pure-token) token=`FT`
      - `mi` (type: pure-token) token=`MI`
  - `box` (type: block)
    - `width` (type: double) token=`BYBOX`
    - `height` (type: double)
    - `unit` (type: oneof)
      - `m` (type: pure-token) token=`M`
      - `km` (type: pure-token) token=`KM`
      - `ft` (type: pure-token) token=`FT`
      - `mi` (type: pure-token) token=`MI`
- `order` (type: oneof) [optional]
  - `asc` (type: pure-token) token=`ASC`
  - `desc` (type: pure-token) token=`DESC`
- `count-block` (type: block) [optional]
  - `count` (type: integer) token=`COUNT`
  - `any` (type: pure-token) token=`ANY` [optional]
- `withcoord` (type: pure-token) token=`WITHCOORD` [optional]
- `withdist` (type: pure-token) token=`WITHDIST` [optional]
- `withhash` (type: pure-token) token=`WITHHASH` [optional]

### `GEOSEARCHSTORE`

v6 arity: `-8` → v7 arity: `-8`  
Group: geo | Since: 6.2.0  
Summary: Queries a geospatial index for members inside an area of a box or a circle, optionally stores the result.

Arguments:
- `destination` (type: key)
- `source` (type: key)
- `from` (type: oneof)
  - `member` (type: string) token=`FROMMEMBER`
  - `fromlonlat` (type: block) token=`FROMLONLAT`
    - `longitude` (type: double)
    - `latitude` (type: double)
- `by` (type: oneof)
  - `circle` (type: block)
    - `radius` (type: double) token=`BYRADIUS`
    - `unit` (type: oneof)
      - `m` (type: pure-token) token=`M`
      - `km` (type: pure-token) token=`KM`
      - `ft` (type: pure-token) token=`FT`
      - `mi` (type: pure-token) token=`MI`
  - `box` (type: block)
    - `width` (type: double) token=`BYBOX`
    - `height` (type: double)
    - `unit` (type: oneof)
      - `m` (type: pure-token) token=`M`
      - `km` (type: pure-token) token=`KM`
      - `ft` (type: pure-token) token=`FT`
      - `mi` (type: pure-token) token=`MI`
- `order` (type: oneof) [optional]
  - `asc` (type: pure-token) token=`ASC`
  - `desc` (type: pure-token) token=`DESC`
- `count-block` (type: block) [optional]
  - `count` (type: integer) token=`COUNT`
  - `any` (type: pure-token) token=`ANY` [optional]
- `storedist` (type: pure-token) token=`STOREDIST` [optional]

### `GET`

v6 arity: `2` → v7 arity: `2`  
Group: string | Since: 1.0.0  
Summary: Returns the string value of a key.

Arguments:
- `key` (type: key)

### `GETBIT`

v6 arity: `3` → v7 arity: `3`  
Group: bitmap | Since: 2.2.0  
Summary: Returns a bit value by offset.

Arguments:
- `key` (type: key)
- `offset` (type: integer)

### `GETDEL`

v6 arity: `2` → v7 arity: `2`  
Group: string | Since: 6.2.0  
Summary: Returns the string value of a key after deleting the key.

Arguments:
- `key` (type: key)

### `GETEX`

v6 arity: `-2` → v7 arity: `-2`  
Group: string | Since: 6.2.0  
Summary: Returns the string value of a key after setting its expiration time.

Arguments:
- `key` (type: key)
- `expiration` (type: oneof) [optional]
  - `seconds` (type: integer) token=`EX`
  - `milliseconds` (type: integer) token=`PX`
  - `unix-time-seconds` (type: unix-time) token=`EXAT`
  - `unix-time-milliseconds` (type: unix-time) token=`PXAT`
  - `persist` (type: pure-token) token=`PERSIST`

### `GETRANGE`

v6 arity: `4` → v7 arity: `4`  
Group: string | Since: 2.4.0  
Summary: Returns a substring of the string stored at a key.

Arguments:
- `key` (type: key)
- `start` (type: integer)
- `end` (type: integer)

### `GETSET`

v6 arity: `3` → v7 arity: `3`  
Group: string | Since: 1.0.0  
Summary: Returns the previous string value of a key after setting it to a new value.

Arguments:
- `key` (type: key)
- `value` (type: string)

### `HDEL`

v6 arity: `-3` → v7 arity: `-3`  
Group: hash | Since: 2.0.0  
Summary: Deletes one or more fields and their values from a hash. Deletes the hash if no fields remain.

Arguments:
- `key` (type: key)
- `field` (type: string) [multiple]

### `HELLO`

v6 arity: `-1` → v7 arity: `-1`  
Group: connection | Since: 6.0.0  
Summary: Handshakes with the Redis server.

Arguments:
- `arguments` (type: block) [optional]
  - `protover` (type: integer)
  - `auth` (type: block) token=`AUTH` [optional]
    - `username` (type: string)
    - `password` (type: string)
  - `clientname` (type: string) token=`SETNAME` [optional]

### `HEXISTS`

v6 arity: `3` → v7 arity: `3`  
Group: hash | Since: 2.0.0  
Summary: Determines whether a field exists in a hash.

Arguments:
- `key` (type: key)
- `field` (type: string)

### `HGET`

v6 arity: `3` → v7 arity: `3`  
Group: hash | Since: 2.0.0  
Summary: Returns the value of a field in a hash.

Arguments:
- `key` (type: key)
- `field` (type: string)

### `HGETALL`

v6 arity: `2` → v7 arity: `2`  
Group: hash | Since: 2.0.0  
Summary: Returns all fields and values in a hash.

Arguments:
- `key` (type: key)

### `HINCRBY`

v6 arity: `4` → v7 arity: `4`  
Group: hash | Since: 2.0.0  
Summary: Increments the integer value of a field in a hash by a number. Uses 0 as initial value if the field doesn't exist.

Arguments:
- `key` (type: key)
- `field` (type: string)
- `increment` (type: integer)

### `HINCRBYFLOAT`

v6 arity: `4` → v7 arity: `4`  
Group: hash | Since: 2.6.0  
Summary: Increments the floating point value of a field by a number. Uses 0 as initial value if the field doesn't exist.

Arguments:
- `key` (type: key)
- `field` (type: string)
- `increment` (type: double)

### `HKEYS`

v6 arity: `2` → v7 arity: `2`  
Group: hash | Since: 2.0.0  
Summary: Returns all fields in a hash.

Arguments:
- `key` (type: key)

### `HLEN`

v6 arity: `2` → v7 arity: `2`  
Group: hash | Since: 2.0.0  
Summary: Returns the number of fields in a hash.

Arguments:
- `key` (type: key)

### `HMGET`

v6 arity: `-3` → v7 arity: `-3`  
Group: hash | Since: 2.0.0  
Summary: Returns the values of all fields in a hash.

Arguments:
- `key` (type: key)
- `field` (type: string) [multiple]

### `HMSET`

v6 arity: `-4` → v7 arity: `-4`  
Group: hash | Since: 2.0.0  
Summary: Sets the values of multiple fields.

Arguments:
- `key` (type: key)
- `data` (type: block) [multiple]
  - `field` (type: string)
  - `value` (type: string)

### `HRANDFIELD`

v6 arity: `-2` → v7 arity: `-2`  
Group: hash | Since: 6.2.0  
Summary: Returns one or more random fields from a hash.

Arguments:
- `key` (type: key)
- `options` (type: block) [optional]
  - `count` (type: integer)
  - `withvalues` (type: pure-token) token=`WITHVALUES` [optional]

### `HSCAN`

v6 arity: `-3` → v7 arity: `-3`  
Group: hash | Since: 2.8.0  
Summary: Iterates over fields and values of a hash.

Arguments:
- `key` (type: key)
- `cursor` (type: integer)
- `pattern` (type: pattern) token=`MATCH` [optional]
- `count` (type: integer) token=`COUNT` [optional]

### `HSET`

v6 arity: `-4` → v7 arity: `-4`  
Group: hash | Since: 2.0.0  
Summary: Creates or modifies the value of a field in a hash.

Arguments:
- `key` (type: key)
- `data` (type: block) [multiple]
  - `field` (type: string)
  - `value` (type: string)

### `HSETNX`

v6 arity: `4` → v7 arity: `4`  
Group: hash | Since: 2.0.0  
Summary: Sets the value of a field in a hash only when the field doesn't exist.

Arguments:
- `key` (type: key)
- `field` (type: string)
- `value` (type: string)

### `HSTRLEN`

v6 arity: `3` → v7 arity: `3`  
Group: hash | Since: 3.2.0  
Summary: Returns the length of the value of a field.

Arguments:
- `key` (type: key)
- `field` (type: string)

### `HVALS`

v6 arity: `2` → v7 arity: `2`  
Group: hash | Since: 2.0.0  
Summary: Returns all values in a hash.

Arguments:
- `key` (type: key)

### `INCR`

v6 arity: `2` → v7 arity: `2`  
Group: string | Since: 1.0.0  
Summary: Increments the integer value of a key by one. Uses 0 as initial value if the key doesn't exist.

Arguments:
- `key` (type: key)

### `INCRBY`

v6 arity: `3` → v7 arity: `3`  
Group: string | Since: 1.0.0  
Summary: Increments the integer value of a key by a number. Uses 0 as initial value if the key doesn't exist.

Arguments:
- `key` (type: key)
- `increment` (type: integer)

### `INCRBYFLOAT`

v6 arity: `3` → v7 arity: `3`  
Group: string | Since: 2.6.0  
Summary: Increment the floating point value of a key by a number. Uses 0 as initial value if the key doesn't exist.

Arguments:
- `key` (type: key)
- `increment` (type: double)

### `INFO`

v6 arity: `-1` → v7 arity: `-1`  
Group: server | Since: 1.0.0  
Summary: Returns information and statistics about the server.

Arguments:
- `section` (type: string) [optional] [multiple]

### `KEYS`

v6 arity: `2` → v7 arity: `2`  
Group: generic | Since: 1.0.0  
Summary: Returns all key names that match a pattern.

Arguments:
- `pattern` (type: pattern)

### `LATENCY|GRAPH`

v6 arity: `3` → v7 arity: `3`  
Group: server | Since: 2.8.13  
Summary: Returns a latency graph for an event.

Arguments:
- `event` (type: string)

### `LATENCY|HISTORY`

v6 arity: `3` → v7 arity: `3`  
Group: server | Since: 2.8.13  
Summary: Returns timestamp-latency samples for an event.

Arguments:
- `event` (type: string)

### `LATENCY|RESET`

v6 arity: `-2` → v7 arity: `-2`  
Group: server | Since: 2.8.13  
Summary: Resets the latency data for one or more events.

Arguments:
- `event` (type: string) [optional] [multiple]

### `LINDEX`

v6 arity: `3` → v7 arity: `3`  
Group: list | Since: 1.0.0  
Summary: Returns an element from a list by its index.

Arguments:
- `key` (type: key)
- `index` (type: integer)

### `LINSERT`

v6 arity: `5` → v7 arity: `5`  
Group: list | Since: 2.2.0  
Summary: Inserts an element before or after another element in a list.

Arguments:
- `key` (type: key)
- `where` (type: oneof)
  - `before` (type: pure-token) token=`BEFORE`
  - `after` (type: pure-token) token=`AFTER`
- `pivot` (type: string)
- `element` (type: string)

### `LLEN`

v6 arity: `2` → v7 arity: `2`  
Group: list | Since: 1.0.0  
Summary: Returns the length of a list.

Arguments:
- `key` (type: key)

### `LMOVE`

v6 arity: `5` → v7 arity: `5`  
Group: list | Since: 6.2.0  
Summary: Returns an element after popping it from one list and pushing it to another. Deletes the list if the last element was moved.

Arguments:
- `source` (type: key)
- `destination` (type: key)
- `wherefrom` (type: oneof)
  - `left` (type: pure-token) token=`LEFT`
  - `right` (type: pure-token) token=`RIGHT`
- `whereto` (type: oneof)
  - `left` (type: pure-token) token=`LEFT`
  - `right` (type: pure-token) token=`RIGHT`

### `LOLWUT`

v6 arity: `-1` → v7 arity: `-1`  
Group: server | Since: 5.0.0  
Summary: Displays computer art and the Redis version

Arguments:
- `version` (type: integer) token=`VERSION` [optional]

### `LPOP`

v6 arity: `-2` → v7 arity: `-2`  
Group: list | Since: 1.0.0  
Summary: Returns the first elements in a list after removing it. Deletes the list if the last element was popped.

Arguments:
- `key` (type: key)
- `count` (type: integer) [optional] since 6.2.0

### `LPOS`

v6 arity: `-3` → v7 arity: `-3`  
Group: list | Since: 6.0.6  
Summary: Returns the index of matching elements in a list.

Arguments:
- `key` (type: key)
- `element` (type: string)
- `rank` (type: integer) token=`RANK` [optional]
- `num-matches` (type: integer) token=`COUNT` [optional]
- `len` (type: integer) token=`MAXLEN` [optional]

### `LPUSH`

v6 arity: `-3` → v7 arity: `-3`  
Group: list | Since: 1.0.0  
Summary: Prepends one or more elements to a list. Creates the key if it doesn't exist.

Arguments:
- `key` (type: key)
- `element` (type: string) [multiple]

### `LPUSHX`

v6 arity: `-3` → v7 arity: `-3`  
Group: list | Since: 2.2.0  
Summary: Prepends one or more elements to a list only when the list exists.

Arguments:
- `key` (type: key)
- `element` (type: string) [multiple]

### `LRANGE`

v6 arity: `4` → v7 arity: `4`  
Group: list | Since: 1.0.0  
Summary: Returns a range of elements from a list.

Arguments:
- `key` (type: key)
- `start` (type: integer)
- `stop` (type: integer)

### `LREM`

v6 arity: `4` → v7 arity: `4`  
Group: list | Since: 1.0.0  
Summary: Removes elements from a list. Deletes the list if the last element was removed.

Arguments:
- `key` (type: key)
- `count` (type: integer)
- `element` (type: string)

### `LSET`

v6 arity: `4` → v7 arity: `4`  
Group: list | Since: 1.0.0  
Summary: Sets the value of an element in a list by its index.

Arguments:
- `key` (type: key)
- `index` (type: integer)
- `element` (type: string)

### `LTRIM`

v6 arity: `4` → v7 arity: `4`  
Group: list | Since: 1.0.0  
Summary: Removes elements from both ends a list. Deletes the list if all elements were trimmed.

Arguments:
- `key` (type: key)
- `start` (type: integer)
- `stop` (type: integer)

### `MEMORY|USAGE`

v6 arity: `-3` → v7 arity: `-3`  
Group: server | Since: 4.0.0  
Summary: Estimates the memory usage of a key.

Arguments:
- `key` (type: key)
- `count` (type: integer) token=`SAMPLES` [optional]

### `MGET`

v6 arity: `-2` → v7 arity: `-2`  
Group: string | Since: 1.0.0  
Summary: Atomically returns the string values of one or more keys.

Arguments:
- `key` (type: key) [multiple]

### `MIGRATE`

v6 arity: `-6` → v7 arity: `-6`  
Group: generic | Since: 2.6.0  
Summary: Atomically transfers a key from one Redis instance to another.

Arguments:
- `host` (type: string)
- `port` (type: integer)
- `key-selector` (type: oneof)
  - `key` (type: key)
  - `empty-string` (type: pure-token)
- `destination-db` (type: integer)
- `timeout` (type: integer)
- `copy` (type: pure-token) token=`COPY` [optional] since 3.0.0
- `replace` (type: pure-token) token=`REPLACE` [optional] since 3.0.0
- `authentication` (type: oneof) [optional]
  - `auth` (type: string) token=`AUTH` since 4.0.7
  - `auth2` (type: block) token=`AUTH2` since 6.0.0
    - `username` (type: string)
    - `password` (type: string)
- `keys` (type: key) token=`KEYS` [optional] [multiple] since 3.0.6

### `MODULE|LOAD`

v6 arity: `-3` → v7 arity: `-3`  
Group: server | Since: 4.0.0  
Summary: Loads a module.

Arguments:
- `path` (type: string)
- `arg` (type: string) [optional] [multiple]

### `MODULE|UNLOAD`

v6 arity: `3` → v7 arity: `3`  
Group: server | Since: 4.0.0  
Summary: Unloads a module.

Arguments:
- `name` (type: string)

### `MOVE`

v6 arity: `3` → v7 arity: `3`  
Group: generic | Since: 1.0.0  
Summary: Moves a key to another database.

Arguments:
- `key` (type: key)
- `db` (type: integer)

### `MSET`

v6 arity: `-3` → v7 arity: `-3`  
Group: string | Since: 1.0.1  
Summary: Atomically creates or modifies the string values of one or more keys.

Arguments:
- `data` (type: block) [multiple]
  - `key` (type: key)
  - `value` (type: string)

### `MSETNX`

v6 arity: `-3` → v7 arity: `-3`  
Group: string | Since: 1.0.1  
Summary: Atomically modifies the string values of one or more keys only when all keys don't exist.

Arguments:
- `data` (type: block) [multiple]
  - `key` (type: key)
  - `value` (type: string)

### `OBJECT|ENCODING`

v6 arity: `3` → v7 arity: `3`  
Group: generic | Since: 2.2.3  
Summary: Returns the internal encoding of a Redis object.

Arguments:
- `key` (type: key)

### `OBJECT|FREQ`

v6 arity: `3` → v7 arity: `3`  
Group: generic | Since: 4.0.0  
Summary: Returns the logarithmic access frequency counter of a Redis object.

Arguments:
- `key` (type: key)

### `OBJECT|IDLETIME`

v6 arity: `3` → v7 arity: `3`  
Group: generic | Since: 2.2.3  
Summary: Returns the time since the last access to a Redis object.

Arguments:
- `key` (type: key)

### `OBJECT|REFCOUNT`

v6 arity: `3` → v7 arity: `3`  
Group: generic | Since: 2.2.3  
Summary: Returns the reference count of a value of a key.

Arguments:
- `key` (type: key)

### `PERSIST`

v6 arity: `2` → v7 arity: `2`  
Group: generic | Since: 2.2.0  
Summary: Removes the expiration time of a key.

Arguments:
- `key` (type: key)

### `PEXPIRE`

v6 arity: `3` → v7 arity: `-3`  
Group: generic | Since: 2.6.0  
Summary: Sets the expiration time of a key in milliseconds.

Arguments:
- `key` (type: key)
- `milliseconds` (type: integer)
- `condition` (type: oneof) [optional] since 7.0.0
  - `nx` (type: pure-token) token=`NX`
  - `xx` (type: pure-token) token=`XX`
  - `gt` (type: pure-token) token=`GT`
  - `lt` (type: pure-token) token=`LT`

### `PEXPIREAT`

v6 arity: `3` → v7 arity: `-3`  
Group: generic | Since: 2.6.0  
Summary: Sets the expiration time of a key to a Unix milliseconds timestamp.

Arguments:
- `key` (type: key)
- `unix-time-milliseconds` (type: unix-time)
- `condition` (type: oneof) [optional] since 7.0.0
  - `nx` (type: pure-token) token=`NX`
  - `xx` (type: pure-token) token=`XX`
  - `gt` (type: pure-token) token=`GT`
  - `lt` (type: pure-token) token=`LT`

### `PFADD`

v6 arity: `-2` → v7 arity: `-2`  
Group: hyperloglog | Since: 2.8.9  
Summary: Adds elements to a HyperLogLog key. Creates the key if it doesn't exist.

Arguments:
- `key` (type: key)
- `element` (type: string) [optional] [multiple]

### `PFCOUNT`

v6 arity: `-2` → v7 arity: `-2`  
Group: hyperloglog | Since: 2.8.9  
Summary: Returns the approximated cardinality of the set(s) observed by the HyperLogLog key(s).

Arguments:
- `key` (type: key) [multiple]

### `PFDEBUG`

v6 arity: `-3` → v7 arity: `3`  
Group: hyperloglog | Since: 2.8.9  
Summary: Internal commands for debugging HyperLogLog values.

Arguments:
- `subcommand` (type: string)
- `key` (type: key)

### `PFMERGE`

v6 arity: `-2` → v7 arity: `-2`  
Group: hyperloglog | Since: 2.8.9  
Summary: Merges one or more HyperLogLog values into a single key.

Arguments:
- `destkey` (type: key)
- `sourcekey` (type: key) [optional] [multiple]

### `PING`

v6 arity: `-1` → v7 arity: `-1`  
Group: connection | Since: 1.0.0  
Summary: Returns the server's liveliness response.

Arguments:
- `message` (type: string) [optional]

### `PSETEX`

v6 arity: `4` → v7 arity: `4`  
Group: string | Since: 2.6.0  
Summary: Sets both string value and expiration time in milliseconds of a key. The key is created if it doesn't exist.

Arguments:
- `key` (type: key)
- `milliseconds` (type: integer)
- `value` (type: string)

### `PSUBSCRIBE`

v6 arity: `-2` → v7 arity: `-2`  
Group: pubsub | Since: 2.0.0  
Summary: Listens for messages published to channels that match one or more patterns.

Arguments:
- `pattern` (type: pattern) [multiple]

### `PSYNC`

v6 arity: `-3` → v7 arity: `-3`  
Group: server | Since: 2.8.0  
Summary: An internal command used in replication.

Arguments:
- `replicationid` (type: string)
- `offset` (type: integer)

### `PTTL`

v6 arity: `2` → v7 arity: `2`  
Group: generic | Since: 2.6.0  
Summary: Returns the expiration time in milliseconds of a key.

Arguments:
- `key` (type: key)

### `PUBLISH`

v6 arity: `3` → v7 arity: `3`  
Group: pubsub | Since: 2.0.0  
Summary: Posts a message to a channel.

Arguments:
- `channel` (type: string)
- `message` (type: string)

### `PUBSUB|CHANNELS`

v6 arity: `-2` → v7 arity: `-2`  
Group: pubsub | Since: 2.8.0  
Summary: Returns the active channels.

Arguments:
- `pattern` (type: pattern) [optional]

### `PUBSUB|NUMSUB`

v6 arity: `-2` → v7 arity: `-2`  
Group: pubsub | Since: 2.8.0  
Summary: Returns a count of subscribers to channels.

Arguments:
- `channel` (type: string) [optional] [multiple]

### `PUNSUBSCRIBE`

v6 arity: `-1` → v7 arity: `-1`  
Group: pubsub | Since: 2.0.0  
Summary: Stops listening to messages published to channels that match one or more patterns.

Arguments:
- `pattern` (type: pattern) [optional] [multiple]

### `RENAME`

v6 arity: `3` → v7 arity: `3`  
Group: generic | Since: 1.0.0  
Summary: Renames a key and overwrites the destination.

Arguments:
- `key` (type: key)
- `newkey` (type: key)

### `RENAMENX`

v6 arity: `3` → v7 arity: `3`  
Group: generic | Since: 1.0.0  
Summary: Renames a key only when the target key name doesn't exist.

Arguments:
- `key` (type: key)
- `newkey` (type: key)

### `REPLICAOF`

v6 arity: `3` → v7 arity: `3`  
Group: server | Since: 5.0.0  
Summary: Configures a server as replica of another, or promotes it to a master.

Arguments:
- `args` (type: oneof)
  - `host-port` (type: block)
    - `host` (type: string)
    - `port` (type: integer)
  - `no-one` (type: block)
    - `no` (type: pure-token) token=`NO`
    - `one` (type: pure-token) token=`ONE`

### `RESTORE`

v6 arity: `-4` → v7 arity: `-4`  
Group: generic | Since: 2.6.0  
Summary: Creates a key from the serialized representation of a value.

Arguments:
- `key` (type: key)
- `ttl` (type: integer)
- `serialized-value` (type: string)
- `replace` (type: pure-token) token=`REPLACE` [optional] since 3.0.0
- `absttl` (type: pure-token) token=`ABSTTL` [optional] since 5.0.0
- `seconds` (type: integer) token=`IDLETIME` [optional] since 5.0.0
- `frequency` (type: integer) token=`FREQ` [optional] since 5.0.0

### `RESTORE-ASKING`

v6 arity: `-4` → v7 arity: `-4`  
Group: server | Since: 3.0.0  
Summary: An internal command for migrating keys in a cluster.

Arguments:
- `key` (type: key)
- `ttl` (type: integer)
- `serialized-value` (type: string)
- `replace` (type: pure-token) token=`REPLACE` [optional] since 3.0.0
- `absttl` (type: pure-token) token=`ABSTTL` [optional] since 5.0.0
- `seconds` (type: integer) token=`IDLETIME` [optional] since 5.0.0
- `frequency` (type: integer) token=`FREQ` [optional] since 5.0.0

### `RPOP`

v6 arity: `-2` → v7 arity: `-2`  
Group: list | Since: 1.0.0  
Summary: Returns and removes the last elements of a list. Deletes the list if the last element was popped.

Arguments:
- `key` (type: key)
- `count` (type: integer) [optional] since 6.2.0

### `RPOPLPUSH`

v6 arity: `3` → v7 arity: `3`  
Group: list | Since: 1.2.0  
Summary: Returns the last element of a list after removing and pushing it to another list. Deletes the list if the last element was popped.

Arguments:
- `source` (type: key)
- `destination` (type: key)

### `RPUSH`

v6 arity: `-3` → v7 arity: `-3`  
Group: list | Since: 1.0.0  
Summary: Appends one or more elements to a list. Creates the key if it doesn't exist.

Arguments:
- `key` (type: key)
- `element` (type: string) [multiple]

### `RPUSHX`

v6 arity: `-3` → v7 arity: `-3`  
Group: list | Since: 2.2.0  
Summary: Appends an element to a list only when the list exists.

Arguments:
- `key` (type: key)
- `element` (type: string) [multiple]

### `SADD`

v6 arity: `-3` → v7 arity: `-3`  
Group: set | Since: 1.0.0  
Summary: Adds one or more members to a set. Creates the key if it doesn't exist.

Arguments:
- `key` (type: key)
- `member` (type: string) [multiple]

### `SCAN`

v6 arity: `-2` → v7 arity: `-2`  
Group: generic | Since: 2.8.0  
Summary: Iterates over the key names in the database.

Arguments:
- `cursor` (type: integer)
- `pattern` (type: pattern) token=`MATCH` [optional]
- `count` (type: integer) token=`COUNT` [optional]
- `type` (type: string) token=`TYPE` [optional] since 6.0.0

### `SCARD`

v6 arity: `2` → v7 arity: `2`  
Group: set | Since: 1.0.0  
Summary: Returns the number of members in a set.

Arguments:
- `key` (type: key)

### `SCRIPT|DEBUG`

v6 arity: `3` → v7 arity: `3`  
Group: scripting | Since: 3.2.0  
Summary: Sets the debug mode of server-side Lua scripts.

Arguments:
- `mode` (type: oneof)
  - `yes` (type: pure-token) token=`YES`
  - `sync` (type: pure-token) token=`SYNC`
  - `no` (type: pure-token) token=`NO`

### `SCRIPT|EXISTS`

v6 arity: `-3` → v7 arity: `-3`  
Group: scripting | Since: 2.6.0  
Summary: Determines whether server-side Lua scripts exist in the script cache.

Arguments:
- `sha1` (type: string) [multiple]

### `SCRIPT|FLUSH`

v6 arity: `-2` → v7 arity: `-2`  
Group: scripting | Since: 2.6.0  
Summary: Removes all server-side Lua scripts from the script cache.

Arguments:
- `flush-type` (type: oneof) [optional] since 6.2.0
  - `async` (type: pure-token) token=`ASYNC`
  - `sync` (type: pure-token) token=`SYNC`

### `SCRIPT|LOAD`

v6 arity: `3` → v7 arity: `3`  
Group: scripting | Since: 2.6.0  
Summary: Loads a server-side Lua script to the script cache.

Arguments:
- `script` (type: string)

### `SDIFF`

v6 arity: `-2` → v7 arity: `-2`  
Group: set | Since: 1.0.0  
Summary: Returns the difference of multiple sets.

Arguments:
- `key` (type: key) [multiple]

### `SDIFFSTORE`

v6 arity: `-3` → v7 arity: `-3`  
Group: set | Since: 1.0.0  
Summary: Stores the difference of multiple sets in a key.

Arguments:
- `destination` (type: key)
- `key` (type: key) [multiple]

### `SELECT`

v6 arity: `2` → v7 arity: `2`  
Group: connection | Since: 1.0.0  
Summary: Changes the selected database.

Arguments:
- `index` (type: integer)

### `SET`

v6 arity: `-3` → v7 arity: `-3`  
Group: string | Since: 1.0.0  
Summary: Sets the string value of a key, ignoring its type. The key is created if it doesn't exist.

Arguments:
- `key` (type: key)
- `value` (type: string)
- `condition` (type: oneof) [optional] since 2.6.12
  - `nx` (type: pure-token) token=`NX`
  - `xx` (type: pure-token) token=`XX`
- `get` (type: pure-token) token=`GET` [optional] since 6.2.0
- `expiration` (type: oneof) [optional]
  - `seconds` (type: integer) token=`EX` since 2.6.12
  - `milliseconds` (type: integer) token=`PX` since 2.6.12
  - `unix-time-seconds` (type: unix-time) token=`EXAT` since 6.2.0
  - `unix-time-milliseconds` (type: unix-time) token=`PXAT` since 6.2.0
  - `keepttl` (type: pure-token) token=`KEEPTTL` since 6.0.0

### `SETBIT`

v6 arity: `4` → v7 arity: `4`  
Group: bitmap | Since: 2.2.0  
Summary: Sets or clears the bit at offset of the string value. Creates the key if it doesn't exist.

Arguments:
- `key` (type: key)
- `offset` (type: integer)
- `value` (type: integer)

### `SETEX`

v6 arity: `4` → v7 arity: `4`  
Group: string | Since: 2.0.0  
Summary: Sets the string value and expiration time of a key. Creates the key if it doesn't exist.

Arguments:
- `key` (type: key)
- `seconds` (type: integer)
- `value` (type: string)

### `SETNX`

v6 arity: `3` → v7 arity: `3`  
Group: string | Since: 1.0.0  
Summary: Set the string value of a key only when the key doesn't exist.

Arguments:
- `key` (type: key)
- `value` (type: string)

### `SETRANGE`

v6 arity: `4` → v7 arity: `4`  
Group: string | Since: 2.2.0  
Summary: Overwrites a part of a string value with another by an offset. Creates the key if it doesn't exist.

Arguments:
- `key` (type: key)
- `offset` (type: integer)
- `value` (type: string)

### `SHUTDOWN`

v6 arity: `-1` → v7 arity: `-1`  
Group: server | Since: 1.0.0  
Summary: Synchronously saves the database(s) to disk and shuts down the Redis server.

Arguments:
- `save-selector` (type: oneof) [optional]
  - `nosave` (type: pure-token) token=`NOSAVE`
  - `save` (type: pure-token) token=`SAVE`
- `now` (type: pure-token) token=`NOW` [optional] since 7.0.0
- `force` (type: pure-token) token=`FORCE` [optional] since 7.0.0
- `abort` (type: pure-token) token=`ABORT` [optional] since 7.0.0

### `SINTER`

v6 arity: `-2` → v7 arity: `-2`  
Group: set | Since: 1.0.0  
Summary: Returns the intersect of multiple sets.

Arguments:
- `key` (type: key) [multiple]

### `SINTERSTORE`

v6 arity: `-3` → v7 arity: `-3`  
Group: set | Since: 1.0.0  
Summary: Stores the intersect of multiple sets in a key.

Arguments:
- `destination` (type: key)
- `key` (type: key) [multiple]

### `SISMEMBER`

v6 arity: `3` → v7 arity: `3`  
Group: set | Since: 1.0.0  
Summary: Determines whether a member belongs to a set.

Arguments:
- `key` (type: key)
- `member` (type: string)

### `SLAVEOF`

v6 arity: `3` → v7 arity: `3`  
Group: server | Since: 1.0.0  
Summary: Sets a Redis server as a replica of another, or promotes it to being a master.

Arguments:
- `args` (type: oneof)
  - `host-port` (type: block)
    - `host` (type: string)
    - `port` (type: integer)
  - `no-one` (type: block)
    - `no` (type: pure-token) token=`NO`
    - `one` (type: pure-token) token=`ONE`

### `SLOWLOG|GET`

v6 arity: `-2` → v7 arity: `-2`  
Group: server | Since: 2.2.12  
Summary: Returns the slow log's entries.

Arguments:
- `count` (type: integer) [optional]

### `SMEMBERS`

v6 arity: `2` → v7 arity: `2`  
Group: set | Since: 1.0.0  
Summary: Returns all members of a set.

Arguments:
- `key` (type: key)

### `SMISMEMBER`

v6 arity: `-3` → v7 arity: `-3`  
Group: set | Since: 6.2.0  
Summary: Determines whether multiple members belong to a set.

Arguments:
- `key` (type: key)
- `member` (type: string) [multiple]

### `SMOVE`

v6 arity: `4` → v7 arity: `4`  
Group: set | Since: 1.0.0  
Summary: Moves a member from one set to another.

Arguments:
- `source` (type: key)
- `destination` (type: key)
- `member` (type: string)

### `SORT`

v6 arity: `-2` → v7 arity: `-2`  
Group: generic | Since: 1.0.0  
Summary: Sorts the elements in a list, a set, or a sorted set, optionally storing the result.

Arguments:
- `key` (type: key)
- `by-pattern` (type: pattern) token=`BY` [optional]
- `limit` (type: block) token=`LIMIT` [optional]
  - `offset` (type: integer)
  - `count` (type: integer)
- `get-pattern` (type: pattern) token=`GET` [optional] [multiple]
- `order` (type: oneof) [optional]
  - `asc` (type: pure-token) token=`ASC`
  - `desc` (type: pure-token) token=`DESC`
- `sorting` (type: pure-token) token=`ALPHA` [optional]
- `destination` (type: key) token=`STORE` [optional]

### `SPOP`

v6 arity: `-2` → v7 arity: `-2`  
Group: set | Since: 1.0.0  
Summary: Returns one or more random members from a set after removing them. Deletes the set if the last member was popped.

Arguments:
- `key` (type: key)
- `count` (type: integer) [optional] since 3.2.0

### `SRANDMEMBER`

v6 arity: `-2` → v7 arity: `-2`  
Group: set | Since: 1.0.0  
Summary: Get one or multiple random members from a set

Arguments:
- `key` (type: key)
- `count` (type: integer) [optional] since 2.6.0

### `SREM`

v6 arity: `-3` → v7 arity: `-3`  
Group: set | Since: 1.0.0  
Summary: Removes one or more members from a set. Deletes the set if the last member was removed.

Arguments:
- `key` (type: key)
- `member` (type: string) [multiple]

### `SSCAN`

v6 arity: `-3` → v7 arity: `-3`  
Group: set | Since: 2.8.0  
Summary: Iterates over members of a set.

Arguments:
- `key` (type: key)
- `cursor` (type: integer)
- `pattern` (type: pattern) token=`MATCH` [optional]
- `count` (type: integer) token=`COUNT` [optional]

### `STRLEN`

v6 arity: `2` → v7 arity: `2`  
Group: string | Since: 2.2.0  
Summary: Returns the length of a string value.

Arguments:
- `key` (type: key)

### `SUBSCRIBE`

v6 arity: `-2` → v7 arity: `-2`  
Group: pubsub | Since: 2.0.0  
Summary: Listens for messages published to channels.

Arguments:
- `channel` (type: string) [multiple]

### `SUBSTR`

v6 arity: `4` → v7 arity: `4`  
Group: string | Since: 1.0.0  
Summary: Returns a substring from a string value.

Arguments:
- `key` (type: key)
- `start` (type: integer)
- `end` (type: integer)

### `SUNION`

v6 arity: `-2` → v7 arity: `-2`  
Group: set | Since: 1.0.0  
Summary: Returns the union of multiple sets.

Arguments:
- `key` (type: key) [multiple]

### `SUNIONSTORE`

v6 arity: `-3` → v7 arity: `-3`  
Group: set | Since: 1.0.0  
Summary: Stores the union of multiple sets in a key.

Arguments:
- `destination` (type: key)
- `key` (type: key) [multiple]

### `SWAPDB`

v6 arity: `3` → v7 arity: `3`  
Group: server | Since: 4.0.0  
Summary: Swaps two Redis databases.

Arguments:
- `index1` (type: integer)
- `index2` (type: integer)

### `TOUCH`

v6 arity: `-2` → v7 arity: `-2`  
Group: generic | Since: 3.2.1  
Summary: Returns the number of existing keys out of those specified after updating the time they were last accessed.

Arguments:
- `key` (type: key) [multiple]

### `TTL`

v6 arity: `2` → v7 arity: `2`  
Group: generic | Since: 1.0.0  
Summary: Returns the expiration time in seconds of a key.

Arguments:
- `key` (type: key)

### `TYPE`

v6 arity: `2` → v7 arity: `2`  
Group: generic | Since: 1.0.0  
Summary: Determines the type of value stored at a key.

Arguments:
- `key` (type: key)

### `UNLINK`

v6 arity: `-2` → v7 arity: `-2`  
Group: generic | Since: 4.0.0  
Summary: Asynchronously deletes one or more keys.

Arguments:
- `key` (type: key) [multiple]

### `UNSUBSCRIBE`

v6 arity: `-1` → v7 arity: `-1`  
Group: pubsub | Since: 2.0.0  
Summary: Stops listening to messages posted to channels.

Arguments:
- `channel` (type: string) [optional] [multiple]

### `WAIT`

v6 arity: `3` → v7 arity: `3`  
Group: generic | Since: 3.0.0  
Summary: Blocks until the asynchronous replication of all preceding write commands sent by the connection is completed.

Arguments:
- `numreplicas` (type: integer)
- `timeout` (type: integer)

### `WATCH`

v6 arity: `-2` → v7 arity: `-2`  
Group: transactions | Since: 2.2.0  
Summary: Monitors changes to keys to determine the execution of a transaction.

Arguments:
- `key` (type: key) [multiple]

### `XACK`

v6 arity: `-4` → v7 arity: `-4`  
Group: stream | Since: 5.0.0  
Summary: Returns the number of messages that were successfully acknowledged by the consumer group member of a stream.

Arguments:
- `key` (type: key)
- `group` (type: string)
- `id` (type: string) [multiple]

### `XADD`

v6 arity: `-5` → v7 arity: `-5`  
Group: stream | Since: 5.0.0  
Summary: Appends a new message to a stream. Creates the key if it doesn't exist.

Arguments:
- `key` (type: key)
- `nomkstream` (type: pure-token) token=`NOMKSTREAM` [optional] since 6.2.0
- `trim` (type: block) [optional]
  - `strategy` (type: oneof)
    - `maxlen` (type: pure-token) token=`MAXLEN`
    - `minid` (type: pure-token) token=`MINID` since 6.2.0
  - `operator` (type: oneof) [optional]
    - `equal` (type: pure-token) token=`=`
    - `approximately` (type: pure-token) token=`~`
  - `threshold` (type: string)
  - `count` (type: integer) token=`LIMIT` [optional] since 6.2.0
- `id-selector` (type: oneof)
  - `auto-id` (type: pure-token) token=`*`
  - `id` (type: string)
- `data` (type: block) [multiple]
  - `field` (type: string)
  - `value` (type: string)

### `XAUTOCLAIM`

v6 arity: `-6` → v7 arity: `-6`  
Group: stream | Since: 6.2.0  
Summary: Changes, or acquires, ownership of messages in a consumer group, as if the messages were delivered to as consumer group member.

Arguments:
- `key` (type: key)
- `group` (type: string)
- `consumer` (type: string)
- `min-idle-time` (type: string)
- `start` (type: string)
- `count` (type: integer) token=`COUNT` [optional]
- `justid` (type: pure-token) token=`JUSTID` [optional]

### `XCLAIM`

v6 arity: `-6` → v7 arity: `-6`  
Group: stream | Since: 5.0.0  
Summary: Changes, or acquires, ownership of a message in a consumer group, as if the message was delivered a consumer group member.

Arguments:
- `key` (type: key)
- `group` (type: string)
- `consumer` (type: string)
- `min-idle-time` (type: string)
- `id` (type: string) [multiple]
- `ms` (type: integer) token=`IDLE` [optional]
- `unix-time-milliseconds` (type: unix-time) token=`TIME` [optional]
- `count` (type: integer) token=`RETRYCOUNT` [optional]
- `force` (type: pure-token) token=`FORCE` [optional]
- `justid` (type: pure-token) token=`JUSTID` [optional]
- `lastid` (type: string) token=`LASTID` [optional]

### `XDEL`

v6 arity: `-3` → v7 arity: `-3`  
Group: stream | Since: 5.0.0  
Summary: Returns the number of messages after removing them from a stream.

Arguments:
- `key` (type: key)
- `id` (type: string) [multiple]

### `XGROUP|CREATE`

v6 arity: `-5` → v7 arity: `-5`  
Group: stream | Since: 5.0.0  
Summary: Creates a consumer group.

Arguments:
- `key` (type: key)
- `group` (type: string)
- `id-selector` (type: oneof)
  - `id` (type: string)
  - `new-id` (type: pure-token) token=`$`
- `mkstream` (type: pure-token) token=`MKSTREAM` [optional]
- `entries-read` (type: integer) token=`ENTRIESREAD` [optional]

### `XGROUP|CREATECONSUMER`

v6 arity: `5` → v7 arity: `5`  
Group: stream | Since: 6.2.0  
Summary: Creates a consumer in a consumer group.

Arguments:
- `key` (type: key)
- `group` (type: string)
- `consumer` (type: string)

### `XGROUP|DELCONSUMER`

v6 arity: `5` → v7 arity: `5`  
Group: stream | Since: 5.0.0  
Summary: Deletes a consumer from a consumer group.

Arguments:
- `key` (type: key)
- `group` (type: string)
- `consumer` (type: string)

### `XGROUP|DESTROY`

v6 arity: `4` → v7 arity: `4`  
Group: stream | Since: 5.0.0  
Summary: Destroys a consumer group.

Arguments:
- `key` (type: key)
- `group` (type: string)

### `XGROUP|SETID`

v6 arity: `-5` → v7 arity: `-5`  
Group: stream | Since: 5.0.0  
Summary: Sets the last-delivered ID of a consumer group.

Arguments:
- `key` (type: key)
- `group` (type: string)
- `id-selector` (type: oneof)
  - `id` (type: string)
  - `new-id` (type: pure-token) token=`$`
- `entriesread` (type: integer) token=`ENTRIESREAD` [optional]

### `XINFO|CONSUMERS`

v6 arity: `4` → v7 arity: `4`  
Group: stream | Since: 5.0.0  
Summary: Returns a list of the consumers in a consumer group.

Arguments:
- `key` (type: key)
- `group` (type: string)

### `XINFO|GROUPS`

v6 arity: `3` → v7 arity: `3`  
Group: stream | Since: 5.0.0  
Summary: Returns a list of the consumer groups of a stream.

Arguments:
- `key` (type: key)

### `XINFO|STREAM`

v6 arity: `-3` → v7 arity: `-3`  
Group: stream | Since: 5.0.0  
Summary: Returns information about a stream.

Arguments:
- `key` (type: key)
- `full-block` (type: block) [optional]
  - `full` (type: pure-token) token=`FULL`
  - `count` (type: integer) token=`COUNT` [optional]

### `XLEN`

v6 arity: `2` → v7 arity: `2`  
Group: stream | Since: 5.0.0  
Summary: Return the number of messages in a stream.

Arguments:
- `key` (type: key)

### `XPENDING`

v6 arity: `-3` → v7 arity: `-3`  
Group: stream | Since: 5.0.0  
Summary: Returns the information and entries from a stream consumer group's pending entries list.

Arguments:
- `key` (type: key)
- `group` (type: string)
- `filters` (type: block) [optional]
  - `min-idle-time` (type: integer) token=`IDLE` [optional] since 6.2.0
  - `start` (type: string)
  - `end` (type: string)
  - `count` (type: integer)
  - `consumer` (type: string) [optional]

### `XRANGE`

v6 arity: `-4` → v7 arity: `-4`  
Group: stream | Since: 5.0.0  
Summary: Returns the messages from a stream within a range of IDs.

Arguments:
- `key` (type: key)
- `start` (type: string)
- `end` (type: string)
- `count` (type: integer) token=`COUNT` [optional]

### `XREAD`

v6 arity: `-4` → v7 arity: `-4`  
Group: stream | Since: 5.0.0  
Summary: Returns messages from multiple streams with IDs greater than the ones requested. Blocks until a message is available otherwise.

Arguments:
- `count` (type: integer) token=`COUNT` [optional]
- `milliseconds` (type: integer) token=`BLOCK` [optional]
- `streams` (type: block) token=`STREAMS`
  - `key` (type: key) [multiple]
  - `id` (type: string) [multiple]

### `XREADGROUP`

v6 arity: `-7` → v7 arity: `-7`  
Group: stream | Since: 5.0.0  
Summary: Returns new or historical messages from a stream for a consumer in a group. Blocks until a message is available otherwise.

Arguments:
- `group-block` (type: block) token=`GROUP`
  - `group` (type: string)
  - `consumer` (type: string)
- `count` (type: integer) token=`COUNT` [optional]
- `milliseconds` (type: integer) token=`BLOCK` [optional]
- `noack` (type: pure-token) token=`NOACK` [optional]
- `streams` (type: block) token=`STREAMS`
  - `key` (type: key) [multiple]
  - `id` (type: string) [multiple]

### `XREVRANGE`

v6 arity: `-4` → v7 arity: `-4`  
Group: stream | Since: 5.0.0  
Summary: Returns the messages from a stream within a range of IDs in reverse order.

Arguments:
- `key` (type: key)
- `end` (type: string)
- `start` (type: string)
- `count` (type: integer) token=`COUNT` [optional]

### `XSETID`

v6 arity: `3` → v7 arity: `-3`  
Group: stream | Since: 5.0.0  
Summary: An internal command for replicating stream values.

Arguments:
- `key` (type: key)
- `last-id` (type: string)
- `entries-added` (type: integer) token=`ENTRIESADDED` [optional] since 7.0.0
- `max-deleted-id` (type: string) token=`MAXDELETEDID` [optional] since 7.0.0

### `XTRIM`

v6 arity: `-4` → v7 arity: `-4`  
Group: stream | Since: 5.0.0  
Summary: Deletes messages from the beginning of a stream.

Arguments:
- `key` (type: key)
- `trim` (type: block)
  - `strategy` (type: oneof)
    - `maxlen` (type: pure-token) token=`MAXLEN`
    - `minid` (type: pure-token) token=`MINID` since 6.2.0
  - `operator` (type: oneof) [optional]
    - `equal` (type: pure-token) token=`=`
    - `approximately` (type: pure-token) token=`~`
  - `threshold` (type: string)
  - `count` (type: integer) token=`LIMIT` [optional] since 6.2.0

### `ZADD`

v6 arity: `-4` → v7 arity: `-4`  
Group: sorted-set | Since: 1.2.0  
Summary: Adds one or more members to a sorted set, or updates their scores. Creates the key if it doesn't exist.

Arguments:
- `key` (type: key)
- `condition` (type: oneof) [optional] since 3.0.2
  - `nx` (type: pure-token) token=`NX`
  - `xx` (type: pure-token) token=`XX`
- `comparison` (type: oneof) [optional] since 6.2.0
  - `gt` (type: pure-token) token=`GT`
  - `lt` (type: pure-token) token=`LT`
- `change` (type: pure-token) token=`CH` [optional] since 3.0.2
- `increment` (type: pure-token) token=`INCR` [optional] since 3.0.2
- `data` (type: block) [multiple]
  - `score` (type: double)
  - `member` (type: string)

### `ZCARD`

v6 arity: `2` → v7 arity: `2`  
Group: sorted-set | Since: 1.2.0  
Summary: Returns the number of members in a sorted set.

Arguments:
- `key` (type: key)

### `ZCOUNT`

v6 arity: `4` → v7 arity: `4`  
Group: sorted-set | Since: 2.0.0  
Summary: Returns the count of members in a sorted set that have scores within a range.

Arguments:
- `key` (type: key)
- `min` (type: double)
- `max` (type: double)

### `ZDIFF`

v6 arity: `-3` → v7 arity: `-3`  
Group: sorted-set | Since: 6.2.0  
Summary: Returns the difference between multiple sorted sets.

Arguments:
- `numkeys` (type: integer)
- `key` (type: key) [multiple]
- `withscores` (type: pure-token) token=`WITHSCORES` [optional]

### `ZDIFFSTORE`

v6 arity: `-4` → v7 arity: `-4`  
Group: sorted-set | Since: 6.2.0  
Summary: Stores the difference of multiple sorted sets in a key.

Arguments:
- `destination` (type: key)
- `numkeys` (type: integer)
- `key` (type: key) [multiple]

### `ZINCRBY`

v6 arity: `4` → v7 arity: `4`  
Group: sorted-set | Since: 1.2.0  
Summary: Increments the score of a member in a sorted set.

Arguments:
- `key` (type: key)
- `increment` (type: integer)
- `member` (type: string)

### `ZINTER`

v6 arity: `-3` → v7 arity: `-3`  
Group: sorted-set | Since: 6.2.0  
Summary: Returns the intersect of multiple sorted sets.

Arguments:
- `numkeys` (type: integer)
- `key` (type: key) [multiple]
- `weight` (type: integer) token=`WEIGHTS` [optional] [multiple]
- `aggregate` (type: oneof) token=`AGGREGATE` [optional]
  - `sum` (type: pure-token) token=`SUM`
  - `min` (type: pure-token) token=`MIN`
  - `max` (type: pure-token) token=`MAX`
- `withscores` (type: pure-token) token=`WITHSCORES` [optional]

### `ZINTERSTORE`

v6 arity: `-4` → v7 arity: `-4`  
Group: sorted-set | Since: 2.0.0  
Summary: Stores the intersect of multiple sorted sets in a key.

Arguments:
- `destination` (type: key)
- `numkeys` (type: integer)
- `key` (type: key) [multiple]
- `weight` (type: integer) token=`WEIGHTS` [optional] [multiple]
- `aggregate` (type: oneof) token=`AGGREGATE` [optional]
  - `sum` (type: pure-token) token=`SUM`
  - `min` (type: pure-token) token=`MIN`
  - `max` (type: pure-token) token=`MAX`

### `ZLEXCOUNT`

v6 arity: `4` → v7 arity: `4`  
Group: sorted-set | Since: 2.8.9  
Summary: Returns the number of members in a sorted set within a lexicographical range.

Arguments:
- `key` (type: key)
- `min` (type: string)
- `max` (type: string)

### `ZMSCORE`

v6 arity: `-3` → v7 arity: `-3`  
Group: sorted-set | Since: 6.2.0  
Summary: Returns the score of one or more members in a sorted set.

Arguments:
- `key` (type: key)
- `member` (type: string) [multiple]

### `ZPOPMAX`

v6 arity: `-2` → v7 arity: `-2`  
Group: sorted-set | Since: 5.0.0  
Summary: Returns the highest-scoring members from a sorted set after removing them. Deletes the sorted set if the last member was popped.

Arguments:
- `key` (type: key)
- `count` (type: integer) [optional]

### `ZPOPMIN`

v6 arity: `-2` → v7 arity: `-2`  
Group: sorted-set | Since: 5.0.0  
Summary: Returns the lowest-scoring members from a sorted set after removing them. Deletes the sorted set if the last member was popped.

Arguments:
- `key` (type: key)
- `count` (type: integer) [optional]

### `ZRANDMEMBER`

v6 arity: `-2` → v7 arity: `-2`  
Group: sorted-set | Since: 6.2.0  
Summary: Returns one or more random members from a sorted set.

Arguments:
- `key` (type: key)
- `options` (type: block) [optional]
  - `count` (type: integer)
  - `withscores` (type: pure-token) token=`WITHSCORES` [optional]

### `ZRANGE`

v6 arity: `-4` → v7 arity: `-4`  
Group: sorted-set | Since: 1.2.0  
Summary: Returns members in a sorted set within a range of indexes.

Arguments:
- `key` (type: key)
- `start` (type: string)
- `stop` (type: string)
- `sortby` (type: oneof) [optional] since 6.2.0
  - `byscore` (type: pure-token) token=`BYSCORE`
  - `bylex` (type: pure-token) token=`BYLEX`
- `rev` (type: pure-token) token=`REV` [optional] since 6.2.0
- `limit` (type: block) token=`LIMIT` [optional] since 6.2.0
  - `offset` (type: integer)
  - `count` (type: integer)
- `withscores` (type: pure-token) token=`WITHSCORES` [optional]

### `ZRANGEBYLEX`

v6 arity: `-4` → v7 arity: `-4`  
Group: sorted-set | Since: 2.8.9  
Summary: Returns members in a sorted set within a lexicographical range.

Arguments:
- `key` (type: key)
- `min` (type: string)
- `max` (type: string)
- `limit` (type: block) token=`LIMIT` [optional]
  - `offset` (type: integer)
  - `count` (type: integer)

### `ZRANGEBYSCORE`

v6 arity: `-4` → v7 arity: `-4`  
Group: sorted-set | Since: 1.0.5  
Summary: Returns members in a sorted set within a range of scores.

Arguments:
- `key` (type: key)
- `min` (type: double)
- `max` (type: double)
- `withscores` (type: pure-token) token=`WITHSCORES` [optional] since 2.0.0
- `limit` (type: block) token=`LIMIT` [optional]
  - `offset` (type: integer)
  - `count` (type: integer)

### `ZRANGESTORE`

v6 arity: `-5` → v7 arity: `-5`  
Group: sorted-set | Since: 6.2.0  
Summary: Stores a range of members from sorted set in a key.

Arguments:
- `dst` (type: key)
- `src` (type: key)
- `min` (type: string)
- `max` (type: string)
- `sortby` (type: oneof) [optional]
  - `byscore` (type: pure-token) token=`BYSCORE`
  - `bylex` (type: pure-token) token=`BYLEX`
- `rev` (type: pure-token) token=`REV` [optional]
- `limit` (type: block) token=`LIMIT` [optional]
  - `offset` (type: integer)
  - `count` (type: integer)

### `ZRANK`

v6 arity: `3` → v7 arity: `-3`  
Group: sorted-set | Since: 2.0.0  
Summary: Returns the index of a member in a sorted set ordered by ascending scores.

Arguments:
- `key` (type: key)
- `member` (type: string)
- `withscore` (type: pure-token) token=`WITHSCORE` [optional]

### `ZREM`

v6 arity: `-3` → v7 arity: `-3`  
Group: sorted-set | Since: 1.2.0  
Summary: Removes one or more members from a sorted set. Deletes the sorted set if all members were removed.

Arguments:
- `key` (type: key)
- `member` (type: string) [multiple]

### `ZREMRANGEBYLEX`

v6 arity: `4` → v7 arity: `4`  
Group: sorted-set | Since: 2.8.9  
Summary: Removes members in a sorted set within a lexicographical range. Deletes the sorted set if all members were removed.

Arguments:
- `key` (type: key)
- `min` (type: string)
- `max` (type: string)

### `ZREMRANGEBYRANK`

v6 arity: `4` → v7 arity: `4`  
Group: sorted-set | Since: 2.0.0  
Summary: Removes members in a sorted set within a range of indexes. Deletes the sorted set if all members were removed.

Arguments:
- `key` (type: key)
- `start` (type: integer)
- `stop` (type: integer)

### `ZREMRANGEBYSCORE`

v6 arity: `4` → v7 arity: `4`  
Group: sorted-set | Since: 1.2.0  
Summary: Removes members in a sorted set within a range of scores. Deletes the sorted set if all members were removed.

Arguments:
- `key` (type: key)
- `min` (type: double)
- `max` (type: double)

### `ZREVRANGE`

v6 arity: `-4` → v7 arity: `-4`  
Group: sorted-set | Since: 1.2.0  
Summary: Returns members in a sorted set within a range of indexes in reverse order.

Arguments:
- `key` (type: key)
- `start` (type: integer)
- `stop` (type: integer)
- `withscores` (type: pure-token) token=`WITHSCORES` [optional]

### `ZREVRANGEBYLEX`

v6 arity: `-4` → v7 arity: `-4`  
Group: sorted-set | Since: 2.8.9  
Summary: Returns members in a sorted set within a lexicographical range in reverse order.

Arguments:
- `key` (type: key)
- `max` (type: string)
- `min` (type: string)
- `limit` (type: block) token=`LIMIT` [optional]
  - `offset` (type: integer)
  - `count` (type: integer)

### `ZREVRANGEBYSCORE`

v6 arity: `-4` → v7 arity: `-4`  
Group: sorted-set | Since: 2.2.0  
Summary: Returns members in a sorted set within a range of scores in reverse order.

Arguments:
- `key` (type: key)
- `max` (type: double)
- `min` (type: double)
- `withscores` (type: pure-token) token=`WITHSCORES` [optional]
- `limit` (type: block) token=`LIMIT` [optional]
  - `offset` (type: integer)
  - `count` (type: integer)

### `ZREVRANK`

v6 arity: `3` → v7 arity: `-3`  
Group: sorted-set | Since: 2.0.0  
Summary: Returns the index of a member in a sorted set ordered by descending scores.

Arguments:
- `key` (type: key)
- `member` (type: string)
- `withscore` (type: pure-token) token=`WITHSCORE` [optional]

### `ZSCAN`

v6 arity: `-3` → v7 arity: `-3`  
Group: sorted-set | Since: 2.8.0  
Summary: Iterates over members and scores of a sorted set.

Arguments:
- `key` (type: key)
- `cursor` (type: integer)
- `pattern` (type: pattern) token=`MATCH` [optional]
- `count` (type: integer) token=`COUNT` [optional]

### `ZSCORE`

v6 arity: `3` → v7 arity: `3`  
Group: sorted-set | Since: 1.2.0  
Summary: Returns the score of a member in a sorted set.

Arguments:
- `key` (type: key)
- `member` (type: string)

### `ZUNION`

v6 arity: `-3` → v7 arity: `-3`  
Group: sorted-set | Since: 6.2.0  
Summary: Returns the union of multiple sorted sets.

Arguments:
- `numkeys` (type: integer)
- `key` (type: key) [multiple]
- `weight` (type: integer) token=`WEIGHTS` [optional] [multiple]
- `aggregate` (type: oneof) token=`AGGREGATE` [optional]
  - `sum` (type: pure-token) token=`SUM`
  - `min` (type: pure-token) token=`MIN`
  - `max` (type: pure-token) token=`MAX`
- `withscores` (type: pure-token) token=`WITHSCORES` [optional]

### `ZUNIONSTORE`

v6 arity: `-4` → v7 arity: `-4`  
Group: sorted-set | Since: 2.0.0  
Summary: Stores the union of multiple sorted sets in a key.

Arguments:
- `destination` (type: key)
- `numkeys` (type: integer)
- `key` (type: key) [multiple]
- `weight` (type: integer) token=`WEIGHTS` [optional] [multiple]
- `aggregate` (type: oneof) token=`AGGREGATE` [optional]
  - `sum` (type: pure-token) token=`SUM`
  - `min` (type: pure-token) token=`MIN`
  - `max` (type: pure-token) token=`MAX`

</details>

---
## Summary

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
