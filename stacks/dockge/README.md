# Dockge

[Dockge](https://github.com/louislam/dockge) is a reactive web UI for managing
`compose.yaml` stacks: create, edit, start, stop, update and watch logs. It
works directly on files, so you can keep using the CLI side by side.

Tip: initialise other stacks from this library into `DOCKGE_STACKS_DIR` and
they show up in Dockge:

```bash
sudo compose-stacks init uptime-kuma /opt/stacks/uptime-kuma
```

## Quick start

```bash
compose-stacks init dockge ./dockge
cd dockge
docker compose up -d
```

Open <http://127.0.0.1:5001> (SSH tunnel: `ssh -L 5001:127.0.0.1:5001 server`)
and create the admin account.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Interface for the published port |
| `DOCKGE_PORT` | `5001` | Host port |
| `DOCKGE_STACKS_DIR` | `/opt/stacks` | Host path for stacks (same path inside) |

## Services and ports

| Service | Port | Purpose |
| --- | --- | --- |
| `dockge` | 127.0.0.1:5001 | Web UI |

## Security

Mounting `/var/run/docker.sock` gives Dockge full control of Docker, which is
equivalent to root on the host. Never publish it on a public interface without
a strong password, and prefer an SSH tunnel or a VPN.

## Backups

Back up `DOCKGE_STACKS_DIR` (your compose files and `.env` files) and the
`dockge_data` volume.

## Upgrading

Change the tag and `docker compose up -d`.

## Links

- Project: <https://github.com/louislam/dockge>
