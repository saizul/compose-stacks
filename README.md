# compose-stacks

[![CI](https://github.com/saizul/compose-stacks/actions/workflows/ci.yml/badge.svg)](https://github.com/saizul/compose-stacks/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**Production-ready Docker Compose stacks you can deploy in one minute**, and a
small CLI that lists them, validates them and writes a `.env` with strong random
secrets for you.

```bash
pipx install git+https://github.com/saizul/compose-stacks
compose-stacks init n8n ./n8n
cd n8n && docker compose up -d
```

Copy-pasting `docker-compose.yml` files from blog posts gets you `:latest` tags,
`MYSQL_ROOT_PASSWORD: example`, databases published on `0.0.0.0` and no
healthchecks. Every stack in this library follows the same rules, and CI checks
them on every pull request:

- **Pinned image versions** (no `:latest`, no floating major tags), verified against the registry
- **Healthchecks** on every service and `depends_on: condition: service_healthy`
- **`restart: unless-stopped`** and **named volumes** for all state
- **Ports bound to `127.0.0.1`** by default, ready for a reverse proxy (Traefik and Caddy stacks included)
- **No secrets in files**: `.env.example` lists every variable, secrets stay empty, `init` generates them
- **Internal networks** for databases where the app does not need them exposed
- A **README per stack** with quick start, configuration, backups and upgrade notes

## Contents

- [Stacks](#stacks)
- [Features](#features)
- [Quick start](#quick-start)
- [Usage](#usage)
- [Configuration](#configuration)
- [Examples](#examples)
- [Docker image](#docker-image)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [Testing](#testing)
- [Security notes](#security-notes)
- [Limitations](#limitations)
- [License](#license)

## Stacks

<!-- stacks:start -->
**18 stacks** across 14 categories.

| Stack | Category | Description | Images |
| --- | --- | --- | --- |
| [ollama-open-webui](stacks/ollama-open-webui/) | ai | Run open-weight language models locally with Ollama and chat with them in Open WebUI | `ollama/ollama` `ghcr.io/open-webui/open-webui` |
| [umami](stacks/umami/) | analytics | Umami cookie-free, GDPR-friendly web analytics with PostgreSQL | `ghcr.io/umami-software/umami` `postgres` |
| [n8n](stacks/n8n/) | automation | n8n workflow automation with PostgreSQL and optional Redis queue mode with workers | `n8nio/n8n` `postgres` `redis` |
| [redis](stacks/redis/) | cache | Redis 8 with password auth, AOF persistence and a memory limit | `redis` |
| [wordpress](stacks/wordpress/) | cms | WordPress on Apache and PHP 8.4 with MariaDB and a Redis object cache | `wordpress` `mariadb` `redis` |
| [mysql-adminer](stacks/mysql-adminer/) | database | MySQL 8.4 LTS with utf8mb4 defaults and the Adminer database UI | `mysql` `adminer` |
| [postgres-pgadmin](stacks/postgres-pgadmin/) | database | PostgreSQL 18 with pgAdmin 4, pre-registered server and SCRAM authentication | `postgres` `dpage/pgadmin4` |
| [gitea](stacks/gitea/) | devtools | Gitea self-hosted Git service (rootless image) with PostgreSQL and SSH on port 2222 | `gitea/gitea` `postgres` |
| [mailpit](stacks/mailpit/) | email | Mailpit SMTP sink with a web UI and API for testing e-mail in development and staging | `axllent/mailpit` |
| [dockge](stacks/dockge/) | management | Dockge web UI to create, edit, start and update Docker Compose stacks on a host | `louislam/dockge` |
| [dozzle](stacks/dozzle/) | management | Dozzle real-time log viewer for all Docker containers on a host, no database needed | `amir20/dozzle` |
| [grafana-prometheus](stacks/grafana-prometheus/) | monitoring | Grafana, Prometheus and node-exporter for host metrics with a provisioned data source | `prom/prometheus` `prom/node-exporter` `grafana/grafana` |
| [uptime-kuma](stacks/uptime-kuma/) | monitoring | Uptime Kuma 2 for HTTP, TCP, DNS and keyword monitoring with status pages and alerts | `louislam/uptime-kuma` |
| [nextcloud](stacks/nextcloud/) | productivity | Nextcloud file sync and collaboration with MariaDB, Redis locking and a cron container | `nextcloud` `mariadb` `redis` |
| [caddy](stacks/caddy/) | proxy | Caddy 2 reverse proxy with automatic HTTPS, HTTP/3, compression and security headers | `caddy` |
| [traefik](stacks/traefik/) | proxy | Traefik v3 reverse proxy with Docker labels, HTTP to HTTPS redirect and Let's Encrypt | `traefik` `traefik/whoami` |
| [meilisearch](stacks/meilisearch/) | search | Meilisearch typo-tolerant search engine in production mode with a master key | `getmeili/meilisearch` |
| [vaultwarden](stacks/vaultwarden/) | security | Vaultwarden password manager server, compatible with the official Bitwarden apps | `vaultwarden/server` |
<!-- stacks:end -->

Missing something? [Request a stack](https://github.com/saizul/compose-stacks/issues/new?template=stack_request.yml)
or [add one yourself](CONTRIBUTING.md#add-a-new-stack): it takes about 30 minutes.

## Features

| Command | What it does |
| --- | --- |
| `compose-stacks list` | Table or JSON of all stacks, filter with `--category` and `--tag` |
| `compose-stacks search <term>` | Ranked search over names, tags, categories, descriptions and images |
| `compose-stacks show <name>` | Services, images, ports, volumes, variables and notes (`--readme`, `--compose`) |
| `compose-stacks init <name> [dir]` | Copies the stack and writes `.env` (mode 600) with random secrets |
| `compose-stacks outdated <dir>...` | Compares deployed folders with the library: image tag changes, new services, new `.env` variables |
| `compose-stacks validate [name\|path\|--all]` | 30+ rules: schema, pinned tags, healthchecks, ports, secrets, optional `docker compose config` |
| `compose-stacks new <name>` | Starts a new stack from the template (for contributors) |
| `compose-stacks categories` / `rules` | Allowed categories and the validation rule table |

- Works offline: the library ships inside the package.
- Only two dependencies: PyYAML and (on Python 3.10) tomli.
- Secrets come from the operating system CSPRNG (`secrets` module), with the
  equivalent `openssl rand` command documented next to every variable.
- `validate --format github` prints inline pull request annotations.

## Quick start

1. Install the CLI (Python 3.10+):

   ```bash
   pipx install git+https://github.com/saizul/compose-stacks
   # or: pip install git+https://github.com/saizul/compose-stacks
   ```

2. Pick a stack and initialise it:

   ```bash
   compose-stacks search monitoring
   compose-stacks init uptime-kuma ~/stacks/uptime-kuma
   ```

3. Start it:

   ```bash
   cd ~/stacks/uptime-kuma
   docker compose up -d
   docker compose ps   # wait until it shows (healthy)
   ```

No Python on the server? Use the [Docker image](#docker-image), or copy a folder
from [`stacks/`](stacks/) by hand: `cp .env.example .env`, fill every empty
secret with `openssl rand -hex 32`, then `docker compose up -d`.

## Usage

```text
$ compose-stacks list --category database
NAME              CATEGORY  TAGS                         DESCRIPTION
----------------  --------  ---------------------------  -----------------------------------------------------
mysql-adminer     database  mysql,adminer,sql            MySQL 8.4 LTS with utf8mb4 defaults and the Adminer …
postgres-pgadmin  database  postgres,postgresql,pgadmin  PostgreSQL 18 with pgAdmin 4, pre-registered server …

$ compose-stacks init wordpress ./blog --set WORDPRESS_PORT=8090
Initialised wordpress in /home/me/blog
  Generated strong random values for: WORDPRESS_DB_PASSWORD, MARIADB_ROOT_PASSWORD, REDIS_PASSWORD
  Set from --set: WORDPRESS_PORT
  .env written with mode 600. Keep it out of version control.

$ compose-stacks validate --all
ok    caddy
ok    dockge
...
18 stack(s) checked: 0 error(s), 0 warning(s)

$ compose-stacks outdated /srv/blog /srv/status
/srv/blog (wordpress): outdated
  wordpress: wordpress:7.1.3-php8.4-apache -> wordpress:7.1.4-php8.4-apache
  .env is missing: WORDPRESS_MEMORY_LIMIT (see .env.example in the library)
/srv/status (uptime-kuma): up to date
```

`outdated` finds the library stack from the `stack.toml` that `init` copies into
the folder (or `--stack NAME`), compares the image of every service after
variable interpolation, and lists variables from the library's `.env.example`
that your `.env` lacks. Services you added yourself are shown but do not count
as outdated. It never changes files: update the tags, read the upstream
release notes, then `docker compose pull && docker compose up -d`. It exits
with `1` when something is outdated, so a cron job or CI step can alert you
after `pip install -U compose-stacks`.

Useful flags:

| Flag | Command | Meaning |
| --- | --- | --- |
| `-f json` | list, show, search, validate, outdated | Machine-readable output |
| `--stack NAME` | outdated | Library stack to compare with when the folder has no `stack.toml` |
| `-f names` | list | One name per line (for scripts) |
| `--set NAME=VALUE` | init | Override any variable (repeatable) |
| `--force` | init | Overwrite `compose.yaml` and `.env` in the target |
| `--no-secrets` | init | Leave secrets empty (bring your own) |
| `--strict` | validate | Warnings fail the run |
| `--docker` / `--require-docker` | validate | Also run `docker compose config` |
| `-f github` | validate | GitHub Actions annotations |
| `-v` | validate | Show hints and info messages |

Exit codes: `0` success, `1` validation failed (or no search results, or `outdated` found changes), `2` usage error.

## Configuration

| Setting | Default | Description |
| --- | --- | --- |
| `--stacks-dir DIR` | | Use your own stacks folder (same layout as `stacks/`) |
| `COMPOSE_STACKS_DIR` | | Same as `--stacks-dir`, as an environment variable |
| (none) | repository `stacks/`, then the bundled copy | Lookup order without the options above |

Every stack is configured through its `.env` file. `compose-stacks show <name>`
lists each variable with its default and whether it is a secret. The common
pattern across all stacks:

| Variable | Default | Meaning |
| --- | --- | --- |
| `BIND_ADDRESS` | `127.0.0.1` | Interface the published ports listen on |
| `<APP>_PORT` | per stack | Host port |
| `*_PASSWORD`, `*_SECRET`, `*_KEY` | generated | Filled by `init`; never committed |

You can point `--stacks-dir` at a private folder to keep company-specific
stacks with the same tooling, and run `compose-stacks validate --stacks-dir ./my-stacks`
in your own CI.

## Examples

The [`examples/`](examples/) folder contains:

- [`vps-quickstart.sh`](examples/vps-quickstart.sh): Caddy in front of WordPress and Uptime Kuma on a fresh VPS
- [`traefik-labels.yaml`](examples/traefik-labels.yaml): routing any stack through the Traefik stack with labels
- [`validate-own-stacks.yml`](examples/validate-own-stacks.yml): GitHub Actions workflow that validates your private stacks folder
- [`list-as-json.py`](examples/list-as-json.py): using the Python API

Python API:

```python
from compose_stacks import Catalog, validate_stack

catalog = Catalog.discover()
for stack in catalog.filter(category="database"):
    report = validate_stack(stack)
    print(stack.name, "ok" if report.ok() else report.errors)
```

## Docker image

A container image is published to the GitHub Container Registry on every push
to `main` and for every release: `ghcr.io/saizul/compose-stacks` (`linux/amd64`
and `linux/arm64`).

```bash
# Browse
docker run --rm ghcr.io/saizul/compose-stacks list

# Initialise a stack into the current folder (files owned by you)
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" \
  ghcr.io/saizul/compose-stacks init gitea /work/gitea

# Validate your own stacks folder
docker run --rm -v "$PWD/my-stacks:/stacks:ro" \
  ghcr.io/saizul/compose-stacks --stacks-dir /stacks validate --all
```

Tags: `latest` (default branch), the short commit SHA and the release version
(for example `0.1.0`). The image runs as an unprivileged user (UID 10001) and
does not contain the Docker CLI, so `validate --docker` is not available inside it.

Build it locally with `docker build -t compose-stacks .`.

## Contributing

Contributions are very welcome, and adding a stack is a great first pull
request. Read [CONTRIBUTING.md](CONTRIBUTING.md) for the step-by-step guide:

```bash
git clone https://github.com/saizul/compose-stacks && cd compose-stacks
python -m venv .venv && . .venv/bin/activate && pip install -e .[dev]
compose-stacks new my-app --category productivity --maintainer your-github-handle
# edit stacks/my-app/*, then:
compose-stacks validate my-app --strict --docker
python scripts/gen_readme.py
```

Good first issues: image tag updates (labelled `stack update`), new stacks from
the [stack requests](https://github.com/saizul/compose-stacks/labels/stack%20request),
and better backup instructions in stack READMEs.

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Roadmap

- `compose-stacks update <dir>`: apply the changes `outdated` reports (with a preview diff)
- `compose-stacks diff <name> <dir>`: compare a deployed folder with the library version
- Optional Traefik labels and Caddy snippets generated per stack
- Scheduled CI job that checks pinned tags against the registries
- More stacks: Paperless-ngx, Immich, Authentik, Plausible, Outline, Mattermost, Jellyfin
- Backup sidecar recipes (restic) for stacks with databases

Ideas and votes are welcome in the issues.

## Testing

```bash
pip install -e .[dev]
pytest                                   # 220+ tests, no network or Docker needed
ruff check . && ruff format --check .
compose-stacks validate --all --strict
compose-stacks validate --all --require-docker   # needs Docker with Compose v2
python scripts/gen_readme.py --check
```

CI runs the tests on Python 3.10 to 3.13, validates every stack offline, runs
`docker compose config` for every stack on a runner with Docker, checks that
the README table is current and builds the container image.

## Security notes

- `init` writes `.env` with permissions `600`. Do not commit it; the
  `.gitignore` of this repository ignores `.env` everywhere.
- Secrets are generated locally with Python's `secrets` module and never leave your machine.
- Stacks that mount `/var/run/docker.sock` (Traefik, Dockge, Dozzle) give the
  container control over Docker, which equals root on the host. Their READMEs
  explain the trade-off. Keep their UIs on `127.0.0.1`.
- Stacks are starting points. Review them, keep the host patched, use a
  firewall and back up your volumes.
- Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md).

## Limitations

- The validator reads Compose files statically. It understands variable
  interpolation, anchors and the short and long port syntax, but it is not a
  full Compose implementation; `--docker` runs the real `docker compose config`.
- `CS044` (credential patterns) is a small regular-expression set. It catches
  common mistakes, not every possible secret.
- Image tags were current when each stack was last updated. Dependabot proposes
  updates weekly; check the upstream release notes before upgrading production.
- Stacks target a single Docker host with Compose v2. Swarm and Kubernetes are out of scope.
- Healthcheck commands depend on tools inside each image (`curl`, `wget`,
  `node`); if an upstream image drops one, the healthcheck needs an update.

## License

[MIT](LICENSE) © 2026 Saizul Amin. Each stack runs third-party software under
its own license; check the upstream project before use.
