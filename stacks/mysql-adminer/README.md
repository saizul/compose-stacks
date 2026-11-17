# MySQL + Adminer

MySQL 8.4 (the long-term support release) with `utf8mb4` as the default
character set, plus [Adminer](https://www.adminer.org), a single-file database
manager.

## Quick start

```bash
compose-stacks init mysql-adminer ./mysql
cd mysql
docker compose up -d
```

Open <http://127.0.0.1:8081>; the server field is pre-filled with `mysql`.
Log in with `MYSQL_USER` / `MYSQL_PASSWORD` from `.env`.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Interface for published ports |
| `MYSQL_PORT` | `3306` | Host port for MySQL |
| `ADMINER_PORT` | `8081` | Host port for Adminer |
| `MYSQL_DATABASE` | `app` | Database created on first start |
| `MYSQL_USER` | `app` | Application user |
| `MYSQL_PASSWORD` | generated | Application user password |
| `MYSQL_ROOT_PASSWORD` | generated | Root password |
| `ADMINER_DESIGN` | `pepa-linha` | Adminer theme |

Adminer is a full database client. Keep it on `127.0.0.1` and use an SSH
tunnel, or stop it when you do not need it: `docker compose stop adminer`.

## Services and ports

| Service | Port | Purpose |
| --- | --- | --- |
| `mysql` | 127.0.0.1:3306 | MySQL |
| `adminer` | 127.0.0.1:8081 | Web UI |

## Backups

```bash
docker compose exec mysql sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --single-transaction --all-databases' > backup.sql
```

## Upgrading

Stay on 8.4.x for LTS updates: change the tag and `docker compose up -d`.

## Links

- MySQL image: <https://hub.docker.com/_/mysql>
- Adminer image: <https://hub.docker.com/_/adminer>
