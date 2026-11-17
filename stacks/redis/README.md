# Redis

A single Redis 8 instance that is safe to leave running on a VPS: password
authentication, append-only persistence (`everysec`), a memory limit and a
port that only listens on `127.0.0.1`.

## Quick start

```bash
compose-stacks init redis ./redis
cd redis
docker compose up -d
docker compose exec redis sh -c 'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli info server'
```

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Interface for the published port |
| `REDIS_PORT` | `6379` | Host port |
| `REDIS_PASSWORD` | generated | Password for the default user |
| `REDIS_MAXMEMORY` | `512mb` | Memory limit |
| `REDIS_MAXMEMORY_POLICY` | `noeviction` | Use `allkeys-lru` for a pure cache |

Connection URL for applications on the host: `redis://127.0.0.1:6379/0` with
the password passed separately (most clients accept a `password` option).

Redis may log a warning about `vm.overcommit_memory`. Set it on the host:
`sudo sysctl -w vm.overcommit_memory=1` (persist it in `/etc/sysctl.d/`).

## Services and ports

| Service | Port | Purpose |
| --- | --- | --- |
| `redis` | 127.0.0.1:6379 | Redis |

## Backups

Copy `appendonlydir/` and `dump.rdb` from the `redis_data` volume, or run
`redis-cli BGSAVE` first and copy `dump.rdb`.

## Upgrading

Change the tag and `docker compose up -d`. Redis reads older AOF/RDB files.

## Links

- Redis image: <https://hub.docker.com/_/redis>
- Persistence: <https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/>
