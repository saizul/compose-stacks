# PostgreSQL + pgAdmin

PostgreSQL 18 with SCRAM-SHA-256 authentication and pgAdmin 4 in server mode.
The PostgreSQL server is pre-registered in pgAdmin through `servers.json`.

## Quick start

```bash
compose-stacks init postgres-pgadmin ./postgres
cd postgres
docker compose up -d
```

- pgAdmin: <http://127.0.0.1:5050> (log in with `PGADMIN_EMAIL` / `PGADMIN_PASSWORD` from `.env`)
- PostgreSQL: `psql "host=127.0.0.1 port=5432 user=postgres dbname=app"`

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Interface for published ports |
| `POSTGRES_PORT` | `5432` | Host port for PostgreSQL |
| `PGADMIN_PORT` | `5050` | Host port for pgAdmin |
| `POSTGRES_DB` | `app` | Database created on first start |
| `POSTGRES_USER` | `postgres` | Superuser |
| `POSTGRES_PASSWORD` | generated | Superuser password |
| `PGADMIN_EMAIL` | `admin@example.com` | pgAdmin login |
| `PGADMIN_PASSWORD` | generated | pgAdmin password |

PostgreSQL 18 images keep data in a version folder under `/var/lib/postgresql`,
which is why the volume is mounted there (not at `/var/lib/postgresql/data`).

## Services and ports

| Service | Port | Purpose |
| --- | --- | --- |
| `postgres` | 127.0.0.1:5432 | PostgreSQL |
| `pgadmin` | 127.0.0.1:5050 | Web UI |

## Backups

```bash
docker compose exec postgres sh -c 'pg_dumpall -U "$POSTGRES_USER"' | gzip > backup.sql.gz
```

## Upgrading

Minor versions (18.x): change the tag and `docker compose up -d`. Major
versions need `pg_dumpall` and a restore into a fresh volume, or `pg_upgrade`.

## Links

- PostgreSQL image: <https://hub.docker.com/_/postgres>
- pgAdmin container docs: <https://www.pgadmin.org/docs/pgadmin4/latest/container_deployment.html>
