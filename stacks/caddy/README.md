# Caddy

[Caddy](https://caddyserver.com) is a web server that obtains and renews TLS
certificates by itself. This stack ships a `Caddyfile` with compression, HSTS
and sane security headers and proxies to an app of your choice.

## Quick start

```bash
compose-stacks init caddy ./caddy --set SITE_DOMAIN=example.com --set UPSTREAM=host.docker.internal:8080
cd caddy
docker compose up -d
docker compose logs -f caddy   # watch the certificate being issued
```

Edit `Caddyfile` to add sites, then reload without downtime:

```bash
docker compose exec -w /etc/caddy caddy caddy reload
```

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `SITE_DOMAIN` | `localhost` | Domain to serve |
| `UPSTREAM` | `host.docker.internal:8080` | Backend for `reverse_proxy` |
| `ACME_EMAIL` | empty | Certificate notices |
| `PUBLIC_BIND_ADDRESS` | `0.0.0.0` | Interface for 80/443 |

### Reaching other stacks

Apps from this library publish on `127.0.0.1`, which a container cannot reach
through `host.docker.internal` on Linux. Two options:

1. Recommended: create a shared network (`docker network create web`), attach
   Caddy and the app to it (`networks: [web]` with `external: true`) and use
   the service name, for example `reverse_proxy wordpress:80`.
2. Set the app's `BIND_ADDRESS` to the docker bridge address (usually `172.17.0.1`).

## Services and ports

| Service | Port | Purpose |
| --- | --- | --- |
| `caddy` | 0.0.0.0:80 | HTTP and ACME |
| `caddy` | 0.0.0.0:443 tcp+udp | HTTPS and HTTP/3 |

## Backups

Back up `caddy_data` (certificates and keys) and your `Caddyfile`.

## Upgrading

Change the tag and `docker compose up -d`.

## Links

- Documentation: <https://caddyserver.com/docs/>
- Caddyfile reverse_proxy: <https://caddyserver.com/docs/caddyfile/directives/reverse_proxy>
