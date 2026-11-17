# Traefik

[Traefik](https://traefik.io/traefik/) routes requests to containers based on
Docker labels and gets TLS certificates from Let's Encrypt automatically. This
stack is a solid single-host edge proxy: HTTP to HTTPS redirect, opt-in routing
(`exposedbydefault=false`), read-only Docker socket and a local-only dashboard.

## Quick start

```bash
compose-stacks init traefik ./traefik --set ACME_EMAIL=you@example.com
cd traefik
docker compose up -d
```

Dashboard: `ssh -L 8080:127.0.0.1:8080 your-server`, then <http://127.0.0.1:8080>.

Test with the demo service: set `COMPOSE_PROFILES=demo` and `WHOAMI_HOST` in
`.env`, point the DNS record at the server and run `docker compose up -d`.

## Route another stack

Add the shared network and labels to the service you want to publish, for
example the WordPress stack:

```yaml
services:
  wordpress:
    networks: [default, backend, proxy]
    labels:
      - traefik.enable=true
      - traefik.http.routers.blog.rule=Host(`blog.example.com`)
      - traefik.http.routers.blog.entrypoints=websecure
      - traefik.http.services.blog.loadbalancer.server.port=80

networks:
  proxy:
    external: true
```

With Traefik in front you can remove the `ports:` section of the routed service.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `ACME_EMAIL` | (required) | Let's Encrypt account e-mail |
| `ACME_CA_SERVER` | production | Use staging while testing |
| `PUBLIC_BIND_ADDRESS` | `0.0.0.0` | Interface for 80/443 |
| `DASHBOARD_BIND_ADDRESS` | `127.0.0.1` | Interface for the dashboard |
| `DASHBOARD_PORT` | `8080` | Dashboard port |
| `TRAEFIK_NETWORK` | `proxy` | Shared network name |
| `TRAEFIK_LOG_LEVEL` | `INFO` | Log level |
| `TRAEFIK_ACCESS_LOG` | `false` | Access log on stdout |
| `COMPOSE_PROFILES` | empty | `demo` starts whoami |
| `WHOAMI_HOST` | `whoami.example.com` | Demo host name |

## Services and ports

| Service | Port | Purpose |
| --- | --- | --- |
| `traefik` | 0.0.0.0:80 | HTTP, ACME challenge, redirect |
| `traefik` | 0.0.0.0:443 | HTTPS |
| `traefik` | 127.0.0.1:8080 | Dashboard |
| `whoami` | via Traefik | Demo (profile `demo`) |

## Security

The Docker socket is mounted read-only, but read access to the Docker API still
reveals environment variables of every container. For stricter setups put a
socket proxy (for example `tecnativa/docker-socket-proxy`) in between.

## Backups

Back up the `letsencrypt` volume (`acme.json`) to avoid re-issuing certificates.

## Upgrading

Change the tag and `docker compose up -d`. Read the migration guides before
moving to a new major version.

## Links

- Documentation: <https://doc.traefik.io/traefik/>
- Docker provider: <https://doc.traefik.io/traefik/providers/docker/>
- Let's Encrypt: <https://doc.traefik.io/traefik/https/acme/>
