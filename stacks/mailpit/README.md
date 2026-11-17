# Mailpit

[Mailpit](https://mailpit.axllent.org) catches every e-mail your application
sends and shows it in a modern web UI, with HTML checks, link checks, spam
scoring and an API for automated tests. It is the maintained successor to
MailHog.

## Quick start

```bash
compose-stacks init mailpit ./mailpit
cd mailpit
docker compose up -d
```

- Web UI: <http://127.0.0.1:8025>
- SMTP: `127.0.0.1:1025`, no TLS, any user name and password

Send a test message:

```bash
printf 'Subject: hello\n\nIt works.\n' | curl -s smtp://127.0.0.1:1025 --mail-from dev@example.com --mail-rcpt you@example.com -T -
```

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Interface for published ports |
| `MAILPIT_UI_PORT` | `8025` | Web UI port |
| `MAILPIT_SMTP_PORT` | `1025` | SMTP port |
| `MP_MAX_MESSAGES` | `5000` | Retention by count |
| `TZ` | `UTC` | Time zone |

Mailpit is a testing tool. Do not expose it publicly: it accepts mail from anyone
who can reach the port.

## Services and ports

| Service | Port | Purpose |
| --- | --- | --- |
| `mailpit` | 127.0.0.1:8025 | Web UI and API |
| `mailpit` | 127.0.0.1:1025 | SMTP |

## Backups

Not usually needed. Messages live in `mailpit_data`.

## Upgrading

Change the tag and `docker compose up -d`.

## Links

- Documentation: <https://mailpit.axllent.org/docs/>
- Runtime options: <https://mailpit.axllent.org/docs/configuration/runtime-options/>
