# Spot architecture (Azure spot workers + stateful workloads)

This doc covers how to deploy stateful services (SQLite, Redis with persistence, anything with local files) on a Docker Swarm cluster where every worker is an Azure Spot VM. Spot eviction can take a worker down with ~30 seconds notice, so the architecture has to assume any worker can vanish.

The cluster has one manager (`live4-mgr-01`) with an attached Azure managed disk, exported as NFS to all workers. Workers are spot. State lives on the NFS share; compute lives on the spot fleet.

The companion rules are `.claude/rules/sqlite.md` (DB pragmas, NFS mount options, single-writer enforcement) and `.claude/rules/spot-resilience.md` (eviction watcher, drain, idempotency, outbox). Read those first if you have not.

## The three reference architectures

Pick one based on cost, write throughput, and HA needs. Every project must be classified into one of these three.

### Architecture A — SQLite on the NFS share (default)

The default for new live4 projects. The DB file lives on `/mnt/nfs/<project>/db/app.db` (NFS export from the manager's Azure managed disk). The application container runs as `replicas: 1` on whichever spot worker the scheduler picks. When that worker is evicted, Swarm reschedules the service onto another spot worker; the new container mounts the same NFS path and opens the same file.

**Cost:** zero extra. Uses the cluster's existing managed disk and NFS export.

**When to use:** single-writer workload, modest write throughput, RPO of "the last committed transaction" is acceptable, RTO of "30-60 seconds for Swarm to reschedule" is acceptable.

**Trade-off:** SQLite-on-NFS is a sharp tool. It works only when the NFS export is configured with `noac`, the SQLite pragmas are correct (no WAL, no `mmap_size`, `synchronous=FULL`, large `busy_timeout`), and the service is enforced to single-writer (`replicas: 1`, `stop-first`, 30 s grace period). The rules in `.claude/rules/sqlite.md` are mandatory, not advisory — skipping any of them produces silent corruption that surfaces hours or days later.

**Compose template:**

```yaml
services:
  api:
    image: 10.2.0.4:5000/2154/myproject_api:${TAG}
    deploy:
      replicas: 1                              # single writer — mandatory for NFS+SQLite
      placement:
        constraints:
          - node.role == worker                # keep workloads off the manager
      update_config:
        order: stop-first                      # old container fully exits before new opens DB
        parallelism: 1
        failure_action: rollback
      rollback_config:
        order: stop-first
      restart_policy:
        condition: any
        delay: 5s
        max_attempts: 3
    stop_grace_period: 30s                     # time to release NFS handles + flush journal
    volumes:
      - type: bind
        source: /mnt/nfs/myproject/db          # NFS share — durable across spot eviction
        target: /data
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8080/health/db"]
      interval: 10s
      timeout: 5s                              # NFS round-trips can be slow on cold mounts
      start_period: 30s
      retries: 3
    networks: [internal, nginx_npm_network]

  # Stateless service — also runs on the spot fleet, no volume needed
  worker:
    image: 10.2.0.4:5000/2154/myproject_worker:${TAG}
    deploy:
      replicas: 3
      placement:
        constraints:
          - node.role == worker
        preferences:
          - spread: node.hostname              # spread across the spot fleet
      update_config:
        order: start-first
        parallelism: 1
        failure_action: rollback
    stop_grace_period: 20s
    networks: [internal]

networks:
  internal:
  nginx_npm_network:
    external: true
```

**Volume:** `/mnt/nfs/myproject/db` is the NFS export from `live4-mgr-01`. The Azure managed disk attached to the manager provides durability; the NFS export is what makes the same file reachable from any spot worker. Snapshots run via `VACUUM INTO` on a schedule plus Azure Backup on the managed disk.

**One-time NFS setup (on the manager):**

```bash
# /etc/exports — single line per project
/mnt/nfs/myproject  10.2.0.0/22(rw,sync,no_subtree_check,no_root_squash)
exportfs -ra
```

`sync` (not `async`) is mandatory — `async` exports lose the durability guarantee SQLite is relying on. `no_subtree_check` avoids spurious `ESTALE` errors on rename.

**One-time NFS mount (on each worker):**

```bash
# /etc/fstab — same on every spot worker
10.2.0.4:/mnt/nfs/myproject  /mnt/nfs/myproject  nfs  nfsvers=4.2,hard,proto=tcp,noac,lookupcache=none,actimeo=0,timeo=600,retrans=2  0 0
```

`noac`, `lookupcache=none`, and `actimeo=0` together disable the attribute caching that breaks SQLite locking on multi-node access. The cost is some extra round-trips per syscall — acceptable for the durability the architecture buys.

### Architecture B — LiteFS for read-heavy workloads

[LiteFS](https://github.com/superfly/litefs) is a FUSE filesystem that replicates SQLite. The primary runs as `replicas: 1` on the spot fleet, the replicas run on other spot workers and serve read traffic locally. Writes are forwarded to the primary via LiteFS proxy.

**When to use:** read:write ratio heavily skewed to reads (typical CMS, marketing sites with mostly cached content), and you want read scaling across the spot fleet without the NFS round-trips on every read.

**Trade-offs:** writes still depend on the primary container being up. Lose the spot worker running the primary and writes fail until LiteFS election picks a new primary (Consul-backed, ~10 seconds). Reads keep working on replicas. LiteFS itself does not eliminate the NFS share — Consul state and primary backups still live on `/mnt/nfs/<project>/litefs-state/`.

**Setup pointers:** the LiteFS sidecar container runs alongside the app container, mounts FUSE at `/litefs`, and the app opens `/litefs/app.db` exactly as it would a local SQLite file. Replication is asynchronous; the app does not need to know.

For full compose examples see the [LiteFS Docker guide](https://fly.io/docs/litefs/getting-started-docker/).

### Architecture C — State out of the cluster

Move the database to [Azure Database for PostgreSQL Flexible Server](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/). The cluster becomes pure stateless and can lose 100% of its workers without data loss.

**Cost:** B1ms (1 vCPU, 2 GB RAM) is ~$13/mo without HA, ~$30/mo with zone-redundant HA.

**When to use:** the project does not have a hard SQLite-specific requirement (embedded analytics, plugin ecosystems, single-file portability), or write throughput is high enough that NFS+SQLite latency matters, or multiple writers are genuinely required.

**Migration cost:** EF Core change provider, regenerate migrations, update connection string. Two days of work for a typical project. Saves indefinitely on the operational complexity of running SQLite on NFS.

## Volume rules of thumb

| Volume                                        | Spot-safe | OK for SQLite writes |
|-----------------------------------------------|-----------|----------------------|
| NFS export from manager (`/mnt/nfs/...`)      | Yes       | Yes — with the SQLite rules in `.claude/rules/sqlite.md` |
| Local bind on a spot worker                   | No        | Never — disk dies on eviction |
| Local bind on the manager                     | No        | Never — manager is not a workload host |
| Azure Files (SMB, any tier)                   | Yes       | No (`mmap` unsafe + lock semantics differ) |
| Blob via `blobfuse2`                          | Yes       | No (eventual consistency) |
| Postgres / managed DB                         | Yes       | N/A (Architecture C) |

The cardinal rule: **one writer at a time on the NFS-backed file.** That is what `replicas: 1` + `stop-first` + 30 s grace period enforce. Break any of those three and you are in the corruption zone — it does not matter how good the pragmas are.

## Required application components

Every service deployed to the cluster must include the following. Code is in `.claude/rules/spot-resilience.md`; this section explains why each piece exists.

### Spot eviction watcher

Polls the Azure IMDS scheduled-events endpoint every 10 seconds. When a `Preempt` event appears, it triggers application shutdown immediately instead of waiting for `SIGTERM`. The eviction notice usually arrives 20-30 seconds before the kill, so this gives the drain pipeline a head start — important on NFS because `SqliteConnection.ClearAllPools()` plus the kernel's NFS flush both take real wall time.

Outside Azure (dev, CI), the IMDS call fails quietly and the watcher is a no-op.

### Graceful drain

The shutdown order matters:

1. **Mark readiness as unready.** The load balancer notices on its next health probe (~3 seconds) and stops sending new requests.
2. **Wait for in-flight requests to finish.** Kestrel's shutdown timeout (configured to 20s) handles this automatically.
3. **Close every `SqliteConnection` and clear the pool.** The kernel can then flush NFS file handles. This is what prevents the next container from opening the DB while the old one's handles are still in flight.
4. **Exit.**

Reverse this order and you will serve `502 Bad Gateway` to clients during shutdown because the LB does not know to stop sending traffic. Skip step 3 and you will eventually see `SQLITE_IOERR (10)` on the next container's first write.

### Idempotent mutation endpoints

Every POST/PUT/PATCH/DELETE accepts an `Idempotency-Key` header. The server stores `(key, response_hash, expires_at)` for 24 hours. A retry with the same key returns the cached response.

Without this, a client that retries after a spot kill mid-write will double-process the operation. For payments and "send email" actions, this is a P0 user-facing bug.

### Outbox pattern for side effects

State changes that trigger external side effects (email, webhook, queue publish) write the *intent* to an `outbox` table inside the same DB transaction. A separate worker drains the outbox. If a spot kill cuts off the publish, the next worker run picks up the unsent row.

Schema sketch:

```sql
CREATE TABLE outbox (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at   TEXT NOT NULL,
    type          TEXT NOT NULL,
    payload       BLOB NOT NULL,
    processed_at  TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    next_attempt  TEXT NOT NULL
);
CREATE INDEX idx_outbox_pending ON outbox(next_attempt) WHERE processed_at IS NULL;
```

Worker drains rows where `processed_at IS NULL AND next_attempt <= now()`, exponential backoff on failure, mark `processed_at = now()` on success.

## Healthcheck strategy

Three separate endpoints, each answering one question:

| Endpoint          | Question                          | Used by                              |
|-------------------|-----------------------------------|--------------------------------------|
| `/health/live`    | Is the process alive?             | Container restart policy             |
| `/health/ready`   | Should the LB send me traffic?    | Load balancer / ingress              |
| `/health/db`      | Is the DB reachable on NFS?       | Swarm `HEALTHCHECK` for replacement  |

`/health/ready` flips to `503` immediately on shutdown via the readiness gate so the LB drains. `/health/live` keeps returning `200` until the process is truly dead. `/health/db` runs `SELECT 1` against the actual connection pool, with a generous timeout (5 s, not 1 s) because NFS lock acquisition can spike under load.

A process that holds a stuck NFS handle but a healthy HTTP listener is the worst kind of zombie. `/health/db` exists to catch it — Swarm replaces the container, the new one mounts NFS fresh.

Implementation:

```csharp
app.MapHealthChecks("/health/live", new HealthCheckOptions
{
    Predicate = _ => false  // no checks, just confirms process is alive
});

app.MapHealthChecks("/health/ready", new HealthCheckOptions
{
    Predicate = check => check.Tags.Contains("ready")
});

app.MapHealthChecks("/health/db", new HealthCheckOptions
{
    Predicate = check => check.Tags.Contains("db")
});
```

Register the DB check with EF Core or `Microsoft.Data.Sqlite`:

```csharp
builder.Services
    .AddHealthChecks()
    .AddCheck<ReadinessCheck>("readiness", tags: ["ready"])
    .AddSqlite(connectionString, name: "sqlite", tags: ["db"]);
```

## Migration path for existing projects

If an existing project currently has SQLite on a worker's local disk (`/var/lib/<project>/...`) or on a different shared-storage path, run the migration in this order:

1. **Inventory the writes.** Find every endpoint and worker that writes to the DB. List them.
2. **Decide on architecture A, B, or C.** A is the default; switch to B or C only if A's single-writer constraint or NFS round-trip cost is genuinely a problem.
3. **Provision the NFS path.** On the manager: `sudo mkdir -p /mnt/nfs/<project>/db /mnt/nfs/<project>/backup` and `chown` to the container user (typically `1000:1000`). Add the export line to `/etc/exports` with `sync,no_subtree_check`. Run `exportfs -ra`.
4. **Mount on each worker.** Add the `nfsvers=4.2,hard,proto=tcp,noac,lookupcache=none,actimeo=0,timeo=600,retrans=2` line to `/etc/fstab`. `mount -a`. Verify the mount is healthy with a small test write.
5. **Snapshot the current DB.** While the service is down: `cp <old-path>/app.db /mnt/nfs/<project>/db/app.db` (and copy any sidecar files). `chown` to the container user.
6. **Update the compose file:** change the bind source to `/mnt/nfs/<project>/db`, set `replicas: 1`, `update_config.order: stop-first`, `stop_grace_period: 30s`, `placement.constraints: [node.role == worker]`.
7. **Verify pragmas.** Confirm the app sets `journal_mode=DELETE`, `synchronous=FULL`, `mmap_size=0`, `busy_timeout=30000`. If it currently uses WAL, that change has to land before the first deploy on NFS — a WAL-mode DB on NFS is the corruption case.
8. **Deploy with `order: stop-first`** so the old container fully exits before the new one opens the DB.
9. **Remove the old volume mount** from the deployment manifest. Leaving it as a fallback invites someone to point the connection string at it again.

Do not run both architectures in parallel "just in case". Pick one, switch, verify, delete the other.
