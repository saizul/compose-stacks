# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-11-17

### Added

- 18 stacks: caddy, dockge, dozzle, gitea, grafana-prometheus, mailpit,
  meilisearch, mysql-adminer, n8n (with optional queue mode), nextcloud,
  ollama-open-webui, postgres-pgadmin, redis, traefik, umami, uptime-kuma,
  vaultwarden and wordpress. All images pinned to the versions current in November 2026.
- `stack.toml` metadata schema (category, tags, ports, volumes, healthchecks,
  environment variables with secret generators, maintainers, upstream docs).
- CLI commands `list`, `show`, `search`, `init`, `validate`, `new`,
  `categories` and `rules`, with table, JSON, names and GitHub output formats.
- `init` writes `.env` with mode 600 and strong random secrets
  (`alnum`, `hex`, `base64`, `urlsafe`, `uuid` generators).
- 31 validation rules (`CS001`-`CS051`), optional `docker compose config` check.
- Stack template and `compose-stacks new` for contributors.
- `scripts/gen_readme.py` keeps the README stack table in sync (checked in CI).
- CI on Python 3.10-3.13, a job running `docker compose config` for every
  stack, container image on `ghcr.io/saizul/compose-stacks`.

[Unreleased]: https://github.com/saizul/compose-stacks/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/saizul/compose-stacks/releases/tag/v0.1.0
