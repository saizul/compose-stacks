# n8n + PostgreSQL

[n8n](https://n8n.io) is a fair-code workflow automation tool, a self-hosted
alternative to Zapier and Make. This stack stores everything in PostgreSQL and
can switch to **queue mode** (Redis plus scalable workers) with two variables.

## Quick start

```bash
compose-stacks init n8n ./n8n
cd n8n
docker compose up -d
```

Open <http://127.0.0.1:5678> and create the owner account.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Interface for the published port |
| `N8N_PORT` | `5678` | Host port |
| `N8N_HOST` / `N8N_PROTOCOL` | `localhost` / `http` | Public address |
| `WEBHOOK_URL` | `http://localhost:5678/` | Base URL that external services call |
| `N8N_SECURE_COOKIE` | `false` | Set `true` behind HTTPS |
| `N8N_PROXY_HOPS` | `1` | Reverse proxies in front of n8n |
| `TZ` | `UTC` | Time zone for the Schedule trigger |
| `POSTGRES_PASSWORD` | generated | Database password |
| `N8N_ENCRYPTION_KEY` | generated | Encrypts saved credentials |
| `EXECUTIONS_MODE` | `regular` | `queue` enables workers |
| `COMPOSE_PROFILES` | empty | `queue` starts Redis and the worker |
| `REDIS_PASSWORD` | generated | Redis password (queue mode) |
| `EXECUTIONS_DATA_MAX_AGE` | `336` | Hours of execution history to keep |

### Production behind HTTPS

```dotenv
N8N_HOST=n8n.example.com
N8N_PROTOCOL=https
WEBHOOK_URL=https://n8n.example.com/
N8N_SECURE_COOKIE=true
```

### Queue mode

```dotenv
EXECUTIONS_MODE=queue
COMPOSE_PROFILES=queue
```

Then `docker compose up -d` and scale workers with
`docker compose up -d --scale n8n-worker=3`.

## Services and ports

| Service | Port | Purpose |
| --- | --- | --- |
| `n8n` | 127.0.0.1:5678 | Editor, API, webhooks |
| `n8n-worker` | internal | Executes jobs (queue profile) |
| `postgres` | internal | PostgreSQL 18 |
| `redis` | internal | Job queue (queue profile) |

## Backups

Back up the `postgres_data` volume (or `pg_dump`) **and** `N8N_ENCRYPTION_KEY`.

```bash
docker compose exec postgres sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > n8n.sql
```

## Upgrading

Read the n8n release notes, change both n8n image tags in `compose.yaml`, then
`docker compose pull && docker compose up -d`. Migrations run on start.
PostgreSQL major upgrades (for example 18 to 19) need `pg_dump`/restore.

## Links

- Docker installation: <https://docs.n8n.io/hosting/installation/docker/>
- Queue mode: <https://docs.n8n.io/hosting/scaling/queue-mode/>
- Environment variables: <https://docs.n8n.io/hosting/configuration/environment-variables/>
