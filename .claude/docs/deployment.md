# CI/CD and deployment

## Cluster infrastructure (live4.se)

All projects are hosted on a Docker Swarm cluster on Azure:

| Node           | Public IP      | Internal IP | Role    |
| -------------- | -------------- | ----------- | ------- |
| live4-mgr-01   | 51.12.246.54   | 10.2.0.4    | Manager |
| live4-wkr-01   | 51.12.246.201  | 10.2.0.5    | Worker  |
| live4-wkr-02   | 51.12.247.158  | 10.2.0.6    | Worker  |
| live4-wkr-03   | 51.12.247.189  | 10.2.0.7    | Worker  |

**SSH access:**

```bash
ssh -i ~/ubuntu/ubuntu ubuntu@51.12.246.54     # Manager (port 22 or 7222)
```

**Private Docker Registry:** `10.2.0.4:5000`
**NFS mount:** `/mnt/nfs/` — shared storage exported from the manager (`live4-mgr-01`) via Azure managed disk, mounted on every worker. This is the **only durable storage** available to the spot fleet, so it holds runtime databases, seed data, build artifacts, and compose files. NFS+SQLite has sharp edges (no WAL, no `mmap`, single writer) — see `.claude/rules/sqlite.md` for the mandatory rules.
**Reverse proxy:** Nginx Proxy Manager (external overlay network `nginx_npm_network`)
**Worker fleet:** All workers are Azure Spot VMs and can be evicted with ~30 seconds notice. Stateful services run on the spot fleet with `replicas: 1` and durable state on the NFS share — see `.claude/docs/spot-architecture.md`.

## Pipeline architecture

```text
GitHub Actions (workflow_dispatch with confirmation)
         │
    Build & Test (.NET)
         │
    Stress Test (API + Frontend) ← MANDATORY, blocks deploy on failure
         │
    Docker Build (multi-stage: sdk → aspnet runtime)
         │
    Save images as TAR → SCP to manager (port 7222)
         │
    Load images → Push to private registry (10.2.0.4:5000)
         │
    Deploy via docker stack deploy (Swarm)
         │
    Verification + Mailjet email notification
```

## GitHub Actions workflow

- **Workflow file**: `.github/workflows/deploy-[projectname].yml`
- **Trigger**: `workflow_dispatch` with `confirm_deploy: "deploy"` as safety mechanism
- **Runner**: `ubuntu-latest`
- **Image tag**: `YYYY.MM.DD-HHMM` (datetime-based)

## Docker

- **Dockerfiles**: Multi-stage builds with `mcr.microsoft.com/dotnet/sdk:10.0` (build) and `aspnet:10.0` (runtime)
- **Registry**: Private at `10.2.0.4:5000`
- **Image naming**: `10.2.0.4:5000/2154/[projectname]_[service]:TAG`
- **Exposed ports**: Configured per project in docker-compose-stack

## Deploy configuration

- **Docker Compose/Stack**: `deploy/docker-compose-stack-[projectname].yml`
- **Deploy script**: `deploy/deploy_[projectname].sh` (replaces image placeholders, deploys stack, sends email)
- **Persistent storage**: `/mnt/nfs/[projectname]/` (databases, seed data, compose files)
- **Networks**: Project-internal overlay network + `nginx_npm_network` (external, for reverse proxy)

## Environment variables and secrets

**GitHub Secrets (configured in repo settings):**

- `LIVE4_SSH_KEY` — SSH key for deployment to the manager node
- `MAILJET_APIKEY` / `MAILJET_SECRET` — Email notifications on deploy

**Production environment (in appsettings.Production.json):**

- `ASPNETCORE_ENVIRONMENT=Production`
- `ConnectionStrings` point to `/data/` — bound from `/mnt/nfs/<project>/db/` (the NFS share exported from `live4-mgr-01`). The managed disk on the manager provides durability across spot eviction; the NFS export makes the same file reachable from any spot worker. See `.claude/rules/sqlite.md` for the mandatory pragmas and the single-writer constraints that make NFS+SQLite safe.

## Storage layout per project

Everything durable lives on the NFS share. The split below is by purpose, not by host — all paths are subdirectories of the same NFS export.

**Shared NFS (`/mnt/nfs/[projectname]/`)** — the only durable storage:

```text
/mnt/nfs/[projectname]/
├── db/
│   ├── app.db                   # Main database — rollback journal mode, no -shm/-wal sidecar
│   └── tenants/                 # Per-tenant databases (if applicable)
│       └── {tenantId}/tenant.db
├── files/                       # User uploads, cached files
├── backup/                      # VACUUM INTO snapshots, hourly
├── seed-data/                   # Initial seed data (read-only at runtime)
├── temp/                        # Staging for Docker images during deploy
└── docker-compose-stack-*.yml   # Resolved compose file
```

The DB lives on NFS because there is no other durable storage available to the spot fleet — the workers' local disks die on spot eviction. To make NFS+SQLite work safely the project must follow the rules in `.claude/rules/sqlite.md`: rollback-journal mode (no WAL), `mmap_size=0`, `busy_timeout=30000`, `synchronous=FULL`, NFS mount with `noac,actimeo=0`, and single-writer enforcement (`replicas: 1`, `update_config.order: stop-first`, `stop_grace_period: 30s`). Skipping any of these turns NFS+SQLite into a corruption generator under load.

## Docker Swarm commands

```bash
docker stack ls                                          # List all stacks
docker stack services [projectname]                      # Status for services
docker stack ps [projectname]                            # Detailed status
docker service logs [projectname]_[service]              # View logs
docker service update --image [new_image] [service]       # Update image
docker service rollback [projectname]_[service]          # Rollback
docker stack rm [projectname]                            # Remove stack
```

## New project — server preparation

When CI/CD is set up for a new project, inform the developer that the following must be created on the server:

**NFS directories (on the manager node) — durable runtime storage:**

```bash
sudo mkdir -p /mnt/nfs/[projectname]/{db,files,backup,seed-data,temp}
sudo mkdir -p /mnt/nfs/[projectname]/db/tenants     # If multi-tenant
sudo chown -R 1000:1000 /mnt/nfs/[projectname]      # Match the container user
sudo chmod -R 770 /mnt/nfs/[projectname]            # Tight perms — NFS-exposed
```

**NFS export (on the manager, one-time per project):**

Add a line to `/etc/exports`:

```text
/mnt/nfs/[projectname]  10.2.0.0/22(rw,sync,no_subtree_check,no_root_squash)
```

Reload exports:

```bash
sudo exportfs -ra
sudo exportfs -v   # verify the export landed
```

`sync` is mandatory — `async` exports lose the durability guarantee SQLite is relying on. `no_subtree_check` avoids spurious `ESTALE` errors on rename.

**NFS mount (on each spot worker, one-time per project):**

Add a line to `/etc/fstab`:

```text
10.2.0.4:/mnt/nfs/[projectname]  /mnt/nfs/[projectname]  nfs  nfsvers=4.2,hard,proto=tcp,noac,lookupcache=none,actimeo=0,timeo=600,retrans=2  0 0
```

Mount and verify:

```bash
sudo mkdir -p /mnt/nfs/[projectname]
sudo mount -a
mount | grep [projectname]   # confirm the mount options applied
```

`noac`, `lookupcache=none`, and `actimeo=0` together disable attribute caching — non-negotiable for SQLite locking on multi-host access. Skipping them produces silent corruption that surfaces hours later.

**Project files that must be created:**

- `deploy/docker-compose-stack-[projectname].yml` — Docker Swarm stack definition
- `deploy/deploy_[projectname].sh` — Deploy script with image placeholder replacement and email notification
- `deploy/update-seed-data.sql` — SQL for initial seed data (if applicable)
- `.github/workflows/deploy-[projectname].yml` — GitHub Actions workflow
- `src/[Service]/Dockerfile` — Multi-stage Dockerfile per service
- `.dockerignore` — Exclude `.git/`, `bin/`, `obj/`, `*.db`, `tests/` etc.
- `src/[Service]/appsettings.Production.json` — Production configuration with `/data/` paths

**GitHub repo settings:**

- Add secret `LIVE4_SSH_KEY` (SSH key for the manager node)
- Add secrets for email notifications (`MAILJET_APIKEY`, `MAILJET_SECRET`)

## Deployment checklist

1. All tests pass locally
2. **Stress tests pass** — both API and frontend (see `.claude/docs/stress-testing.md`)
3. Code is pushed to the correct branch
4. Workflow triggered manually with `confirm_deploy: "deploy"`
5. Verify that images were built and pushed to registry
6. Check Docker Swarm services: `docker stack services [projectname]`
7. Verify email notification (Mailjet)
8. Test the application via its public URL
