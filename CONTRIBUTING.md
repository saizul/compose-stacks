# Contributing to compose-stacks

Thank you for helping! This project lives from contributions: new stacks,
version bumps, better docs and validator improvements are all welcome. You do
not need to be a Python developer to add a stack.

- [Ways to contribute](#ways-to-contribute)
- [Development setup](#development-setup)
- [Add a new stack](#add-a-new-stack)
- [Update an existing stack](#update-an-existing-stack)
- [Stack rules](#stack-rules)
- [Validation rule reference](#validation-rule-reference)
- [Changing the CLI](#changing-the-cli)
- [Pull request process](#pull-request-process)

## Ways to contribute

| Size | Idea |
| --- | --- |
| 5 minutes | Bump a pinned image tag after reading the upstream release notes |
| 15 minutes | Improve the backup or upgrade section of a stack README |
| 30 minutes | Add a new stack (see below), for example one from the [stack requests](https://github.com/saizul/compose-stacks/labels/stack%20request) |
| 1 hour | Add a validation rule or a CLI feature from the roadmap |

Issues labelled `good first issue` are a good place to start. Comment on the
issue so that nobody else works on the same thing.

## Development setup

```bash
git clone https://github.com/saizul/compose-stacks
cd compose-stacks
python -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e .[dev]
pytest
```

Docker with Compose v2 is needed only to start stacks and for `validate --docker`.

## Add a new stack

### 1. Check that it fits

A good stack is popular self-hosted software with an **official container
image**, maintained upstream, and useful to many people. One folder per use
case: for example `postgres-pgadmin`, not one folder per database version.

### 2. Create the folder from the template

```bash
compose-stacks new paperless --category productivity --maintainer your-github-handle
```

This creates `stacks/paperless/` from [`templates/stack/`](templates/stack/):

```text
stacks/paperless/
  compose.yaml     # the services
  .env.example     # every variable, secrets left empty
  stack.toml       # metadata used by the CLI, the README table and the validator
  README.md        # quick start, configuration, ports, backups, upgrading, links
```

Extra config files (for example `Caddyfile` or `prometheus/prometheus.yml`)
go into the same folder and are mounted read-only with relative paths.

### 3. Write `compose.yaml`

Start from the upstream Compose example and apply the library conventions:

```yaml
services:
  app:
    image: ghcr.io/example/app:2.4.1          # exact version, never latest
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    environment:
      DB_PASSWORD: ${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in .env}
    ports:
      - "${BIND_ADDRESS:-127.0.0.1}:${APP_PORT:-8000}:8000"
    volumes:
      - app_data:/data
    healthcheck:
      test: ["CMD-SHELL", "curl -fsS http://127.0.0.1:8000/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
```

Tips:

- Find the current tag on the registry (Docker Hub, GHCR, Quay) and in the
  upstream release notes. Prefer full versions such as `18.7-alpine` over `18`.
- Check which tools the image has for the healthcheck: `docker run --rm --entrypoint sh IMAGE -c 'command -v curl wget'`.
  Node images can use `node -e "fetch(...)"`; many apps ship their own command (`/mailpit readyz`, `traefik healthcheck`).
  If a service really cannot have one (a `scratch` image), add an exemption with a reason in `stack.toml`.
- Escape `$` as `$$` when the container shell should expand a variable.
- Databases and caches that only the app talks to should not publish ports.
  Put them on an `internal: true` network when the app has other network needs.
- Do not set `container_name` (it blocks running a stack twice) or the obsolete `version:` key.

### 4. Write `.env.example`

List **every** variable used in `compose.yaml`. Secrets stay empty and get a
hint comment, which `init` replaces with a random value:

```dotenv
BIND_ADDRESS=127.0.0.1
APP_PORT=8000

# Generate: openssl rand -hex 24
POSTGRES_PASSWORD=
```

Use `hex` or `alnum` generators for values that end up inside URLs.

### 5. Write `stack.toml`

```toml
name = "paperless"                       # must equal the folder name
description = "Short sentence without a trailing period, max 160 characters"
category = "productivity"                # compose-stacks categories
tags = ["paperless", "documents", "ocr"]
upstream_docs = "https://docs.example.org/docker"
maintained_by = ["your-github-handle"]
notes = "Optional one-line hint printed after init"

[[ports]]                                # one entry per published port
service = "app"
host = 8000
container = 8000
bind = "127.0.0.1"                       # "0.0.0.0" only if it must be public
description = "Web UI"

[[volumes]]                              # one entry per named volume
name = "app_data"
description = "Documents and thumbnails"

[healthcheck]
services = ["app", "db"]                 # services that define a healthcheck
# exempt = { worker = "Reason why it cannot have one" }

[env.POSTGRES_PASSWORD]                  # one table per variable in .env.example
description = "Database password"
secret = true
generate = "hex:24"                      # alnum:N, hex:N, base64:N, urlsafe:N or uuid
```

### 6. Write the stack README

Keep the section order of the template: **Quick start**, **Configuration**
(table of variables), **Services and ports**, **Backups**, **Upgrading**, **Links**.
Mention anything a first-time user would trip over.

### 7. Validate and test

```bash
compose-stacks validate paperless --strict -v    # offline rules
compose-stacks validate paperless --docker       # plus docker compose config
compose-stacks init paperless /tmp/paperless
cd /tmp/paperless && docker compose up -d && docker compose ps
```

Every service should reach `(healthy)`. Open the app once and click through
the first-run setup.

### 8. Update the README table and open the pull request

```bash
python scripts/gen_readme.py
pytest
```

Commit the stack folder and README.md, then open a pull request. The template
contains a checklist; CI runs the same checks.

## Update an existing stack

1. Read the upstream release notes for breaking changes.
2. Change the tag in `compose.yaml` (all services that use the image).
3. Run `compose-stacks validate <name> --docker` and, ideally, upgrade a running copy.
4. Mention migration steps in the stack README under **Upgrading** if needed.

Dependabot opens weekly pull requests for image updates. Reviews of those are very welcome too.

## Stack rules

The validator enforces most rules. In short:

1. Pinned versions, published images only (no `build:`).
2. Healthcheck and restart policy on every service.
3. Named volumes for state, documented in `stack.toml`.
4. Published ports on `${BIND_ADDRESS:-127.0.0.1}` unless they must be public.
5. No secrets in any file. No example passwords, no credentials in URLs.
6. Every variable is in `.env.example` and described in `stack.toml`.
7. Telemetry off where the app supports it.

## Validation rule reference

| Code | Level | Rule |
| --- | --- | --- |
| CS001 | error | A required file is missing (compose.yaml, .env.example, README.md, stack.toml) |
| CS002 | error | stack.toml cannot be parsed |
| CS003 | error | stack.toml does not match the schema |
| CS004 | error | stack.toml 'name' must equal the folder name |
| CS005 | warning | README.md is missing a recommended section |
| CS010 | error | compose.yaml cannot be parsed |
| CS011 | warning | The top-level 'version' key is obsolete |
| CS012 | error | Every service must use a published image (no 'build') |
| CS013 | error | Image tags must be pinned (no missing tag, no :latest or other floating tags) |
| CS014 | warning | Major-only tags (for example postgres:18) float across minor releases |
| CS015 | error | Every service needs a healthcheck or a documented exemption |
| CS016 | error | healthcheck.services in stack.toml does not match compose.yaml |
| CS017 | warning | Services should set a restart policy |
| CS018 | warning | container_name prevents running a stack twice on one host |
| CS019 | warning | privileged containers need a very good reason |
| CS020 | error | Invalid port mapping syntax |
| CS021 | error | Port binding does not match stack.toml (127.0.0.1 is the default) |
| CS022 | error | Published ports in compose.yaml and stack.toml must match |
| CS030 | error | A volume listed in stack.toml is not declared in compose.yaml |
| CS031 | warning | A named volume in compose.yaml is not documented in stack.toml |
| CS040 | error | compose.yaml uses a variable that .env.example does not define |
| CS041 | error | A variable from stack.toml is missing in .env.example |
| CS042 | error | Secret variables must be empty in .env.example |
| CS043 | error | Hardcoded secret value in compose.yaml |
| CS044 | error | Something that looks like a real credential was found in a stack file |
| CS045 | warning | A variable in .env.example is not described in stack.toml |
| CS046 | warning | Secret variables should carry a generation hint comment in .env.example |
| CS047 | warning | A variable looks secret but is not marked secret = true in stack.toml |
| CS048 | warning | The default in stack.toml differs from the value in .env.example |
| CS050 | error | docker compose config failed |
| CS051 | info | docker is not available, the docker compose config check was skipped |

List them in the terminal with `compose-stacks rules`.

## Changing the CLI

The code is in `src/compose_stacks/`:

| Module | Responsibility |
| --- | --- |
| `cli.py` | argparse commands and exit codes |
| `catalog.py` | finding and loading stacks, filtering and search |
| `metadata.py` | `stack.toml` schema |
| `compose.py` | Compose and `.env` parsing helpers |
| `validate.py` | validation rules (`RULES` table) |
| `docker.py` | optional `docker compose config` check |
| `scaffold.py` | `init` and `new` |
| `generators.py` | random secret generators |
| `render.py` | text, JSON, Markdown and GitHub output |

To add a validation rule: add a code to `RULES` in `validate.py`, implement
the check, add a test in `tests/test_validate.py` that triggers it, and make
sure `pytest` (which validates the whole library strictly) still passes.

Style: `ruff check . && ruff format .`, type hints, no new runtime dependencies
without discussion. Tests must not need network access or Docker.

## Pull request process

1. Fork, create a branch (`stack/paperless`, `fix/validate-ports`).
2. Keep pull requests focused: one stack or one change.
3. Fill in the pull request checklist.
4. A maintainer reviews within a few days. Stacks you add list you in
   `maintained_by`, and you will be asked to review future changes to them.

By contributing you agree that your work is released under the MIT License and
that you follow the [Code of Conduct](CODE_OF_CONDUCT.md).
