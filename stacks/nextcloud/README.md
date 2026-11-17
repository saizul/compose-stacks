# Nextcloud

[Nextcloud](https://nextcloud.com) gives you files, calendars, contacts and
office apps on your own server. This stack follows the upstream Docker
recommendations: MariaDB with `READ-COMMITTED` and row-based binlogs, Redis for
transactional file locking and a separate container for background jobs.

## Quick start

```bash
compose-stacks init nextcloud ./nextcloud
cd nextcloud
docker compose up -d
docker compose logs -f nextcloud   # first start installs Nextcloud (1-3 minutes)
```

Open <http://127.0.0.1:8082> and log in with `NEXTCLOUD_ADMIN_USER` and the
generated `NEXTCLOUD_ADMIN_PASSWORD` from `.env`.

Switch background jobs to **Cron** in *Administration settings > Basic settings*;
the `cron` container runs them every five minutes.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Interface for the published port |
| `NEXTCLOUD_PORT` | `8082` | Host port |
| `NEXTCLOUD_TRUSTED_DOMAINS` | `localhost` | Host names users open |
| `OVERWRITEPROTOCOL` | `http` | `https` behind a TLS proxy |
| `TRUSTED_PROXIES` | private ranges | Proxies allowed to set client IPs |
| `NEXTCLOUD_ADMIN_USER` | `admin` | Admin user |
| `NEXTCLOUD_ADMIN_PASSWORD` | generated | Admin password |
| `MYSQL_PASSWORD` | generated | Database password |
| `MARIADB_ROOT_PASSWORD` | generated | MariaDB root password |
| `REDIS_PASSWORD` | generated | Redis password |
| `PHP_MEMORY_LIMIT` | `1024M` | PHP memory limit |
| `PHP_UPLOAD_LIMIT` | `16G` | Maximum upload size |

Behind a proxy, also forward `/.well-known/carddav` and `/.well-known/caldav`
to `/remote.php/dav` and raise the proxy body size limit.

## Services and ports

| Service | Port | Purpose |
| --- | --- | --- |
| `nextcloud` | 127.0.0.1:8082 | Web UI and WebDAV |
| `cron` | internal | Background jobs |
| `db` | internal | MariaDB 11.8 |
| `redis` | internal | File locking and cache |

## Backups

Enable maintenance mode, dump the database, archive the volume, disable maintenance mode:

```bash
docker compose exec -u www-data nextcloud php occ maintenance:mode --on
docker compose exec db sh -c 'mariadb-dump -uroot -p"$MARIADB_ROOT_PASSWORD" --single-transaction nextcloud' > nextcloud.sql
docker run --rm -v "$(basename "$PWD")_nextcloud_data:/data:ro" -v "$PWD:/backup" alpine tar czf /backup/nextcloud-files.tgz -C /data .
docker compose exec -u www-data nextcloud php occ maintenance:mode --off
```

## Upgrading

Nextcloud only supports upgrading **one major version at a time**. Change both
image tags (`nextcloud` and `cron`) to the next major, `docker compose up -d`,
and wait for the upgrade to finish before moving to the next one.

## Links

- Docker image: <https://github.com/nextcloud/docker>
- Admin manual: <https://docs.nextcloud.com/server/latest/admin_manual/>
