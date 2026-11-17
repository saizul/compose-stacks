# WordPress + MariaDB + Redis

The classic WordPress setup, hardened for a VPS: the official Apache image,
MariaDB 11.8 LTS and Redis for the object cache. MariaDB and Redis sit on an
internal Docker network without internet access, and the site is published on
`127.0.0.1` so that only your reverse proxy can reach it.

## Quick start

```bash
compose-stacks init wordpress ./wordpress
cd wordpress
docker compose up -d
docker compose ps        # wait for (healthy)
```

Open <http://127.0.0.1:8080> (or your proxied domain) and finish the installer.
Then install and enable the **Redis Object Cache** plugin; the connection
settings are already in `wp-config.php`.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Interface for the published port |
| `WORDPRESS_PORT` | `8080` | Host port |
| `WORDPRESS_DB_NAME` | `wordpress` | Database name |
| `WORDPRESS_DB_USER` | `wordpress` | Database user |
| `WORDPRESS_TABLE_PREFIX` | `wp_` | Table prefix |
| `WORDPRESS_DB_PASSWORD` | generated | Database user password |
| `MARIADB_ROOT_PASSWORD` | generated | MariaDB root password |
| `REDIS_PASSWORD` | generated | Redis password |
| `REDIS_MAXMEMORY` | `256mb` | Redis memory cap (LRU eviction) |

`DISALLOW_FILE_EDIT` is enabled, so the theme and plugin editors in wp-admin are
turned off. Remove that line from `WORDPRESS_CONFIG_EXTRA` if you need them.

### Behind a reverse proxy

The official image already trusts `X-Forwarded-Proto`, so HTTPS works behind
Traefik, Caddy or Nginx. With Caddy:

```caddyfile
example.com {
	reverse_proxy 127.0.0.1:8080
}
```

## Services and ports

| Service | Port | Purpose |
| --- | --- | --- |
| `wordpress` | 127.0.0.1:8080 | Website and wp-admin |
| `db` | internal | MariaDB 11.8 |
| `redis` | internal | Object cache |

## Backups

```bash
# Database
docker compose exec db sh -c 'mariadb-dump -uroot -p"$MARIADB_ROOT_PASSWORD" --single-transaction --all-databases' > db.sql
# Files (uploads, themes, plugins)
docker run --rm -v "$(basename "$PWD")_wordpress_data:/data:ro" -v "$PWD:/backup" alpine tar czf /backup/wp-files.tgz -C /data .
```

## Upgrading

Change the image tag in `compose.yaml`, then `docker compose pull && docker compose up -d`.
`MARIADB_AUTO_UPGRADE=1` runs `mariadb-upgrade` automatically after a MariaDB
upgrade. Take a database backup first.

## Links

- Image documentation: <https://hub.docker.com/_/wordpress>
- MariaDB image: <https://hub.docker.com/_/mariadb>
- Redis Object Cache plugin: <https://wordpress.org/plugins/redis-cache/>
