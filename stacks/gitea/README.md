# Gitea + PostgreSQL

[Gitea](https://about.gitea.com) is a lightweight self-hosted Git service with
issues, pull requests, packages and Actions. This stack uses the **rootless**
image (runs as UID 1000, built-in SSH server) and PostgreSQL.

## Quick start

```bash
compose-stacks init gitea ./gitea
cd gitea
docker compose up -d
```

Open <http://127.0.0.1:3000>. The database settings are pre-filled from the
environment; create the administrator account in the *Administrator account
settings* section and click **Install Gitea**.

Clone over SSH: `git clone ssh://git@your-server:2222/owner/repo.git`

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Interface for HTTP |
| `GITEA_HTTP_PORT` | `3000` | Host port for HTTP |
| `SSH_BIND_ADDRESS` | `0.0.0.0` | Interface for SSH |
| `GITEA_SSH_PORT` | `2222` | Host port for SSH |
| `GITEA_DOMAIN` | `localhost` | Public host name |
| `GITEA_ROOT_URL` | `http://localhost:3000/` | Public URL |
| `GITEA_DISABLE_REGISTRATION` | `true` | Close self sign-up |
| `POSTGRES_PASSWORD` | generated | Database password |

Any `app.ini` setting can be set with `GITEA__section__KEY` variables; add them
under `environment:` in `compose.yaml`.

## Services and ports

| Service | Port | Purpose |
| --- | --- | --- |
| `gitea` | 127.0.0.1:3000 | Web UI |
| `gitea` | 0.0.0.0:2222 | Git over SSH |
| `db` | internal | PostgreSQL 18 |

## Backups

```bash
docker compose exec gitea gitea dump -c /etc/gitea/app.ini --file /tmp/gitea-dump.zip
docker compose cp gitea:/tmp/gitea-dump.zip .
```

## Upgrading

Change the tag, then `docker compose pull && docker compose up -d`. Gitea runs
database migrations on start. Read the release notes for breaking changes.

## Links

- Rootless Docker install: <https://docs.gitea.com/installation/install-with-docker-rootless>
- Configuration cheat sheet: <https://docs.gitea.com/administration/config-cheat-sheet>
