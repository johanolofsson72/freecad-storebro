---
paths:
  - "**/appsettings*.json"
  - "**/docker-compose*.yml"
  - "**/Program.cs"
  - "**/*Db*.cs"
  - "**/*Sqlite*.cs"
---

# SQLite rules

SQLite is the default database for this stack. The live4 cluster runs all workers as Azure Spot VMs and uses an NFS share exported from the manager (`live4-mgr-01`, Azure managed disk) as the only durable storage available to the spot fleet. SQLite therefore lives on NFS by design — the manager keeps the disk, the spot workers come and go.

NFS+SQLite is a known sharp-edges combination. The rules below exist so it works reliably anyway. They are mandatory for every SQLite-using service deployed to live4.

## Volume placement (BLOCKING)

| Storage type                                         | SQLite write workload? | Notes |
|------------------------------------------------------|------------------------|-------|
| NFS share from `live4-mgr-01` (`/mnt/nfs/...`)       | Yes                    | The supported architecture. Requires the rules below. |
| Local bind mount on a spot worker                    | No                     | Disk dies with the spot VM on eviction. Anything written between snapshots is lost. |
| Local bind mount on the manager (`live4-mgr-01`)     | No                     | The manager is for management, registry, and NFS export — not application workloads. Use the NFS path instead. |
| SMB / Azure Files (any tier)                         | No                     | Locking semantics differ from NFSv4 in ways SQLite does not handle. |
| Blob via `blobfuse2` or any object-store FUSE        | No                     | Eventual consistency. Will silently lose writes. |

The "default" answer for any new SQLite database on live4 is `/mnt/nfs/<project>/db/app.db`. The mgr-attached managed disk is what gives the data durability across spot eviction; the NFS export is what makes the data reachable from whichever spot worker the container lands on.

## NFS export configuration (one-time, on the manager)

The export must be configured to match SQLite's lock and consistency expectations. Mount options on the workers:

```text
nfsvers=4.2,hard,proto=tcp,noac,lookupcache=none,actimeo=0,timeo=600,retrans=2
```

`noac` (no attribute caching) is non-negotiable. Without it, two processes that briefly overlap on the same DB file see different `mtime`/size values and SQLite's locking protocol breaks silently. `lookupcache=none` and `actimeo=0` reinforce the same property for filename and inode lookups. The cost is some extra round-trips per syscall — acceptable for the durability guarantee.

NFSv4.2 (or 4.1) is required. NFSv3's lock manager (`rpc.lockd`) has known races on lease recovery that produce `SQLITE_IOERR` under load.

If the export is currently configured without these options, that is a P0 infrastructure defect — fix the mount before relying on the rules below.

## Required pragmas (run once per connection / at startup)

NFS does not support cross-host `mmap` consistency, so WAL mode and `mmap_size > 0` are forbidden. The DB runs in rollback-journal mode with full fsync.

```csharp
await conn.ExecuteAsync("PRAGMA journal_mode=DELETE;");    // rollback journal — NFS-safe
await conn.ExecuteAsync("PRAGMA synchronous=FULL;");       // pay full fsync — NFS needs it
await conn.ExecuteAsync("PRAGMA busy_timeout=30000;");     // 30s — NFS lock acquisition can be slow
await conn.ExecuteAsync("PRAGMA foreign_keys=ON;");
await conn.ExecuteAsync("PRAGMA temp_store=MEMORY;");
await conn.ExecuteAsync("PRAGMA mmap_size=0;");            // no mmap on NFS, ever
await conn.ExecuteAsync("PRAGMA cache_size=-20000;");      // 20 MB page cache in process
```

`busy_timeout=0` is forbidden. `journal_mode=WAL` is forbidden. `mmap_size > 0` is forbidden. Each of these turns NFS-safe SQLite into a corruption generator.

If the project has an internal-only DB on a local volume that is not shared (caches, scratch DBs that can be rebuilt), WAL is permitted there — but the connection string and pragmas must be clearly different from the durable NFS DB. Do not mix them in one helper.

## Connection string

```csharp
var cs = new SqliteConnectionStringBuilder
{
    DataSource     = dbPath,                       // e.g. /data/app.db (bind to /mnt/nfs/<project>/db)
    Mode           = SqliteOpenMode.ReadWriteCreate,
    Cache          = SqliteCacheMode.Shared,
    Pooling        = true,
    DefaultTimeout = 60,                            // longer than busy_timeout — NFS round-trips
}.ToString();
```

`Cache = Shared` enables the in-process shared cache so multiple connections in the same app share locks coherently — important on NFS where every cross-process lock is a network round-trip. Pooling stays on; opening a fresh connection per query multiplies NFS overhead.

## Single-writer enforcement (BLOCKING)

NFS+SQLite tolerates concurrent readers but only ever one writer at a time across the whole cluster. Enforcement happens at three levels:

1. **`replicas: 1`** in compose. Multiple replicas across multiple spot workers would race on the same file via NFS — guaranteed corruption.
2. **`update_config.order: stop-first`** so the old container fully releases the DB before the new one opens it. `start-first` is forbidden for SQLite-using services.
3. **`stop_grace_period: 30s`** so the old container has time to close `SqliteConnection` pools, finish in-flight writes, and let NFS flush before exit.

If the workload genuinely needs more than one writer, the answer is Architecture B (LiteFS) or Architecture C (Postgres) — not "more replicas of the SQLite service". See `.claude/docs/spot-architecture.md`.

## Lifecycle: graceful shutdown is mandatory

The shutdown handler must release every connection and clear the pool so the kernel actually flushes file handles before the container exits. On NFS, a half-flushed handle held by an exiting process is the worst-case window for journal corruption.

```csharp
public sealed class SqliteShutdown(string connectionString) : IHostedService
{
    public Task StartAsync(CancellationToken _) => Task.CompletedTask;

    public async Task StopAsync(CancellationToken ct)
    {
        // Force a no-op write to flush any pending journal frames on disk
        await using var conn = new SqliteConnection(connectionString);
        await conn.OpenAsync(ct);
        await conn.ExecuteAsync("PRAGMA wal_checkpoint(TRUNCATE);"); // no-op in DELETE mode, safe to call
        await conn.ExecuteAsync("PRAGMA optimize;");                 // analyze stats before exit
        await conn.CloseAsync();

        // Drop every pooled handle so NFS sees the file released
        SqliteConnection.ClearAllPools();
    }
}
```

Register early in DI so it runs during `IHostedService` shutdown. Pair with `stop_grace_period: 30s` in compose.

## Retry on transient errors

NFS produces `SQLITE_BUSY (5)`, `SQLITE_LOCKED (6)`, and `SQLITE_IOERR (10)` more often than local disk — usually transient, usually recoverable. Wrap every write with a retry policy:

```csharp
var retry = Policy
    .Handle<SqliteException>(e => e.SqliteErrorCode is 5 or 6 or 10)
    .WaitAndRetryAsync(
        retryCount: 6,
        sleepDurationProvider: attempt => TimeSpan.FromMilliseconds(150 * Math.Pow(2, attempt)));
```

Six attempts with exponential backoff covers most NFS lock-acquisition windows. Do **not** retry `SQLITE_CORRUPT (11)` — that is a permanent failure. Surface it as fatal so the service restarts and the operator can restore from the latest snapshot.

## Snapshots and backups

NFS keeps the file alive across spot eviction, but it does not protect against logical corruption, accidental `DELETE`, or the rare hard-NFS-failure case. Every project must run snapshots:

- Hourly: `VACUUM INTO '/mnt/nfs/<project>/backup/app-{ISO8601}.db'`. Keep 24 hours.
- Daily: copy the latest hourly snapshot to Azure Blob (Litestream-style continuous streaming is also acceptable and preferred for high-write projects).
- Weekly: prune local snapshots older than 7 days.

`VACUUM INTO` produces a consistent copy without locking the source for long; safe to run during traffic.

## Forbidden patterns

- `journal_mode=WAL` on any DB whose volume is NFS, SMB, or any FUSE-backed storage. The `-shm` file does not work cross-host.
- `PRAGMA mmap_size` set to anything but `0` on an NFS-backed DB.
- `replicas: 2` (or more) on a SQLite-using service.
- `update_config.order: start-first` on a SQLite-using service.
- `stop_grace_period` shorter than `30s` on a SQLite-using service.
- `busy_timeout=0` or omitting `busy_timeout` entirely.
- Catching `SqliteException` for `SQLITE_CORRUPT (11)` and continuing — it must propagate as fatal.
- Opening a fresh `SqliteConnection` per query in a hot path without pooling.
- Mixing the durable NFS DB connection string with a local-disk cache DB connection string in the same helper without explicit naming (`Db_Main` vs `Db_Cache`).
