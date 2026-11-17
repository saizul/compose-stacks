# __NAME__

One or two sentences: what the software is and why someone would self-host it.

## Quick start

```bash
compose-stacks init __NAME__ ./__NAME__
cd __NAME__
docker compose up -d
docker compose ps
```

Open <http://127.0.0.1:8080>.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Interface for published ports |
| `APP_PORT` | `8080` | Host port for the web UI |
| `APP_SECRET` | generated | Session signing secret |

## Services and ports

| Service | Port | Purpose |
| --- | --- | --- |
| `app` | 127.0.0.1:8080 | Web UI |

## Backups

Explain which volumes hold state and how to back them up.

## Upgrading

Explain how to move to a new image tag and anything that needs migrating.

## Links

- Upstream documentation: <https://example.org/docs>
