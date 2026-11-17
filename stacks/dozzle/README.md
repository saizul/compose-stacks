# Dozzle

[Dozzle](https://dozzle.dev) streams the logs of every container on the host
to your browser, with search, split view and SQL-style log queries. It stores
nothing and needs no database.

## Quick start

```bash
compose-stacks init dozzle ./dozzle
cd dozzle
docker compose up -d
```

Open <http://127.0.0.1:8888> (SSH tunnel: `ssh -L 8888:127.0.0.1:8888 server`).

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Interface for the published port |
| `DOZZLE_PORT` | `8888` | Host port |
| `DOZZLE_ENABLE_ACTIONS` | `false` | Start/stop/restart buttons |
| `DOZZLE_HOSTNAME` | empty | Host label in the UI |

To add a login, follow the upstream *Authentication* guide (file-based users
with `DOZZLE_AUTH_PROVIDER=simple`).

## Services and ports

| Service | Port | Purpose |
| --- | --- | --- |
| `dozzle` | 127.0.0.1:8888 | Web UI |

## Security

Logs often contain secrets and personal data. The Docker socket is mounted
read-only, but anyone who reaches the UI can read every container's logs.

## Backups

Nothing to back up.

## Upgrading

Change the tag and `docker compose up -d`.

## Links

- Getting started: <https://dozzle.dev/guide/getting-started>
- Authentication: <https://dozzle.dev/guide/authentication>
