# Umami

[Umami](https://umami.is) is a simple, fast, privacy-focused alternative to
Google Analytics. It does not use cookies, so most sites can run it without a
consent banner.

## Quick start

```bash
compose-stacks init umami ./umami
cd umami
docker compose up -d
```

Open <http://127.0.0.1:3002>, log in with the default account **admin / umami**
and change the password right away under *Settings > Profile*.

Add a website and paste the tracking snippet into your site:

```html
<script defer src="https://stats.example.com/script.js" data-website-id="YOUR-ID"></script>
```

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Interface for the published port |
| `UMAMI_PORT` | `3002` | Host port |
| `POSTGRES_PASSWORD` | generated | Database password (hex, URL-safe) |
| `APP_SECRET` | generated | Session signing secret |
| `TRACKER_SCRIPT_NAME` | `script.js` | Rename to dodge ad blockers |

## Services and ports

| Service | Port | Purpose |
| --- | --- | --- |
| `umami` | 127.0.0.1:3002 | Dashboard and tracker |
| `db` | internal | PostgreSQL 18 |

## Backups

```bash
docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > umami.sql.gz
```

## Upgrading

Change the tag and `docker compose up -d`; database migrations run on start.
Read the release notes before a major upgrade.

## Links

- Install docs: <https://umami.is/docs/install>
- Environment variables: <https://umami.is/docs/environment-variables>
