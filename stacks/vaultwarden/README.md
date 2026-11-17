# Vaultwarden

[Vaultwarden](https://github.com/dani-garcia/vaultwarden) is an unofficial,
lightweight Bitwarden-compatible server written in Rust. Use the official
Bitwarden browser extensions, desktop and mobile apps with it.

## Quick start

```bash
compose-stacks init vaultwarden ./vaultwarden --set VAULTWARDEN_DOMAIN=https://vault.example.com
cd vaultwarden
docker compose up -d
```

Point your TLS reverse proxy at `127.0.0.1:8222`, open the HTTPS URL and create
your account. Then disable sign-ups:

```bash
sed -i 's/^SIGNUPS_ALLOWED=.*/SIGNUPS_ALLOWED=false/' .env
docker compose up -d
```

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Interface for the published port |
| `VAULTWARDEN_PORT` | `8222` | Host port |
| `VAULTWARDEN_DOMAIN` | `https://vault.example.com` | Public URL |
| `SIGNUPS_ALLOWED` | `true` | Turn off after creating accounts |
| `INVITATIONS_ALLOWED` | `true` | Organisation invitations |
| `ADMIN_TOKEN` | generated | Enables `/admin` |
| `LOG_LEVEL` | `warn` | Log level |

### Hash the admin token

A plain-text `ADMIN_TOKEN` works, but Vaultwarden warns about it. Create an
Argon2 hash and store it instead (escape each `$` as `$$` in `.env`):

```bash
docker compose exec vaultwarden /vaultwarden hash --preset owasp
```

## Services and ports

| Service | Port | Purpose |
| --- | --- | --- |
| `vaultwarden` | 127.0.0.1:8222 | Web vault, API, WebSocket notifications |

## Backups

The whole state lives in the `vaultwarden_data` volume. Back up `db.sqlite3`
with `sqlite3 db.sqlite3 ".backup backup.sqlite3"` plus the `attachments/`,
`sends/` folders and `rsa_key*` files. Test restores regularly: this is your
password vault.

## Upgrading

Change the tag and `docker compose up -d`.

## Links

- Wiki: <https://github.com/dani-garcia/vaultwarden/wiki>
- Proxy examples: <https://github.com/dani-garcia/vaultwarden/wiki/Proxy-examples>
