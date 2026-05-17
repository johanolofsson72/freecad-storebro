---
paths:
  - "**/Program.cs"
  - "**/docker-compose*.yml"
  - "**/Controllers/**/*.cs"
  - "**/Endpoints/**/*.cs"
  - "**/Services/**/*.cs"
  - "**/Workers/**/*.cs"
---

# Spot resilience rules

Production sites run on Azure Spot VMs as Swarm workers. Every worker can be evicted with ~30 seconds notice, so containers must assume they will be killed mid-operation. The rules below are non-negotiable for any service deployed to the live4 cluster.

## Architecture (BLOCKING)

The cluster has one manager (`live4-mgr-01`) and three spot workers. **All workers are spot.** There is no reserved/non-spot worker. Stateful services run on whichever spot worker the scheduler picks; durability comes from the NFS share exported from the manager (Azure managed disk → NFS → mounted on every worker).

Every project's compose file must therefore:

1. Mount durable state from `/mnt/nfs/<project>/...` (the NFS export, not local-disk on a worker).
2. Run stateful services with `replicas: 1`, `update_config.order: stop-first`, and `stop_grace_period: 30s`.
3. Keep workloads off the manager — the manager handles SSH, registry, and NFS export. Use `placement.constraints: [node.role == worker]` to keep services on the spot fleet only.

For SQLite-specific PRAGMAs, NFS mount options, and the single-writer enforcement model, see `.claude/rules/sqlite.md`. For the full reference architectures (NFS-shared SQLite, LiteFS for read-heavy, managed Postgres for state-out-of-cluster), see `.claude/docs/spot-architecture.md`.

## Required components in every service

### 1. Spot eviction watcher

Polls Azure's Instance Metadata Service (IMDS) for `Preempt` / `Terminate` / `Reboot` events and triggers `IHostApplicationLifetime.StopApplication()` so the drain starts ~20 seconds earlier than waiting for `SIGTERM`.

```csharp
public sealed class SpotEvictionWatcher(
    IHostApplicationLifetime lifetime,
    ILogger<SpotEvictionWatcher> log,
    HttpClient http) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        http.DefaultRequestHeaders.Add("Metadata", "true");
        const string url = "http://169.254.169.254/metadata/scheduledevents?api-version=2020-07-01";

        while (!ct.IsCancellationRequested)
        {
            try
            {
                var doc = await http.GetFromJsonAsync<JsonElement>(url, ct);
                if (doc.TryGetProperty("Events", out var events))
                {
                    foreach (var ev in events.EnumerateArray())
                    {
                        var type = ev.GetProperty("EventType").GetString();
                        if (type is "Preempt" or "Terminate" or "Reboot")
                        {
                            log.LogWarning("Spot eviction notice received: {Type}. Draining.", type);
                            lifetime.StopApplication();
                            return;
                        }
                    }
                }
            }
            catch (Exception ex) { log.LogDebug(ex, "IMDS poll failed"); }

            await Task.Delay(TimeSpan.FromSeconds(10), ct);
        }
    }
}
```

Register in DI:

```csharp
builder.Services.AddHttpClient<SpotEvictionWatcher>();
builder.Services.AddHostedService<SpotEvictionWatcher>();
```

The watcher is a no-op outside Azure (IMDS calls fail and are caught), so it is safe to keep in dev environments.

### 2. Graceful drain

Order matters. The first thing to do on shutdown is fail readiness so the load balancer drains traffic, then finish in-flight requests, then flush state and release file handles. Reverse this order and you serve errors during shutdown — or worse, leave half-flushed SQLite handles open on NFS.

```csharp
public sealed class GracefulDrain(
    IReadinessGate readiness,
    ILogger<GracefulDrain> log) : IHostedService
{
    public Task StartAsync(CancellationToken _) => Task.CompletedTask;

    public async Task StopAsync(CancellationToken _)
    {
        readiness.MarkUnready();
        log.LogInformation("Readiness flipped to unready — waiting for LB drain");
        await Task.Delay(TimeSpan.FromSeconds(3));
    }
}
```

Configure Kestrel to allow in-flight work to finish:

```csharp
builder.WebHost.UseShutdownTimeout(TimeSpan.FromSeconds(20));
```

In compose, give the container time to checkpoint, drain, and release NFS handles:

```yaml
deploy:
  update_config:
    order: stop-first
  stop_grace_period: 30s
```

`stop-first` is mandatory for SQLite-using services. If the new container opens the NFS-backed DB while the old one still holds it, NFS lock contention plus journal recovery on a stale view of the file is the textbook NFS+SQLite corruption window.

### 3. Idempotent writes

Every endpoint that mutates state must accept an `Idempotency-Key` header (UUID v4, client-generated). The server stores `(key, response_hash, expires_at)` and returns the cached response on replay.

```csharp
app.MapPost("/orders", async (
    Order order,
    [FromHeader(Name = "Idempotency-Key")] Guid key,
    IIdempotencyStore store) =>
{
    if (await store.TryReplay(key) is { } cached) return cached;
    var result = await CreateOrder(order);
    await store.Save(key, result);
    return result;
});
```

Without idempotency, retries from the LB or the client after a spot kill silently double-charge users.

### 4. Outbox for reliable side effects

Anything that triggers a side effect (email, webhook, message queue publish) must be written to an `outbox` table in the same DB transaction as the state change. A separate worker drains the outbox. Spot kills mid-publish? The next worker run picks up the unsent row. No "fire and forget" calls allowed.

## Forbidden patterns

- A service running stateful workloads on a worker's local disk (anywhere outside `/mnt/nfs/<project>/...`). The local volume dies with the spot VM on eviction.
- A service running on `live4-mgr-01` (no `placement.constraints: [node.role == worker]`). The manager is for management, registry, and NFS export — not application traffic.
- A POST/PUT/PATCH/DELETE endpoint without idempotency support.
- A side-effect call (email, webhook, queue publish) outside the outbox.
- A SQLite-using service with `replicas > 1`, with `update_config.order: start-first`, or with `stop_grace_period < 30s`. Each one is a guaranteed NFS+SQLite corruption path under load.
- A `docker-compose*.yml` for a stateful service whose `volumes:` section binds anywhere other than `/mnt/nfs/<project>/...` (or a sibling NFS path) for the durable data.
- Authoritative state held only in `IMemoryCache` or in-process buffers. Recoverable cache (read-through, derivable) is fine; authoritative is not — the process can vanish in 30 seconds.

## Healthchecks

Healthchecks must hit the actual dependency, not just `/health`. A process that returns HTTP 200 while its DB connection is broken lies to Swarm and gets traffic it cannot serve. On NFS, "broken DB connection" includes "the NFS server is reachable but lock acquisition is timing out" — `/health/db` must catch that.

```dockerfile
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
  CMD wget -qO- http://localhost:8080/health/db || exit 1
```

The `--timeout=5s` and `--start-period=30s` are tuned for NFS — local-disk SQLite would use 3s/20s. NFS round-trips on cold mounts can run a few seconds long; tighter values produce false-negative restarts.

`/health/db` runs `SELECT 1 FROM sqlite_master LIMIT 1` (or equivalent) against the connection pool. `/health/live` (process is alive) and `/health/ready` (ready to receive traffic, flips on drain) are separate endpoints.
