# Uptime Kuma

[Uptime Kuma](https://github.com/louislam/uptime-kuma) monitors websites,
ports, DNS records, Docker containers and more, and sends alerts to 90+
notification services. Version 2 keeps the simple single-container setup.

## Quick start

```bash
compose-stacks init uptime-kuma ./uptime-kuma
cd uptime-kuma
docker compose up -d
```

Open <http://127.0.0.1:3001> and create the admin account.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Interface for the published port |
| `UPTIME_KUMA_PORT` | `3001` | Host port |
| `TZ` | `UTC` | Time zone |

Uptime Kuma uses WebSockets; make sure your reverse proxy forwards them
(Caddy and Traefik do this automatically).

To monitor containers on the same host, add
`- /var/run/docker.sock:/var/run/docker.sock:ro` under `volumes:`. This gives
the container read access to the Docker API, so only do it if you need it.

## Services and ports

| Service | Port | Purpose |
| --- | --- | --- |
| `uptime-kuma` | 127.0.0.1:3001 | Dashboard and status pages |

## Backups

Stop the stack and archive the `uptime_kuma_data` volume, or use
**Settings > Backup** in the UI.

## Upgrading

Change the tag, then `docker compose pull && docker compose up -d`. Read the
release notes before upgrading across major versions.

## Links

- Wiki: <https://github.com/louislam/uptime-kuma/wiki>
