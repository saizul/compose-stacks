## What does this pull request do?

<!-- One or two sentences. Link the issue: "Closes #123". -->

## Type

- [ ] New stack
- [ ] Stack update (image tags, config)
- [ ] CLI / validator change
- [ ] Documentation

## Checklist for stacks

- [ ] The folder has `compose.yaml`, `.env.example`, `README.md` and `stack.toml`
- [ ] Every image is pinned to a specific version (no `latest`, no major-only tags)
- [ ] I checked that the tags exist on the registry and read the upstream release notes
- [ ] Every service has a healthcheck (or an exemption with a reason in `stack.toml`) and `restart: unless-stopped`
- [ ] Ports bind to `${BIND_ADDRESS:-127.0.0.1}` unless they must be public (and `bind = "0.0.0.0"` says so)
- [ ] No passwords, tokens or keys in any file; secrets are empty in `.env.example` with an `openssl rand` hint
- [ ] `compose-stacks validate <name> --strict --docker` passes
- [ ] I started the stack with `compose-stacks init <name> /tmp/<name> && docker compose up -d` and all services became healthy
- [ ] `python scripts/gen_readme.py` was run and the README table is updated

## Checklist for code

- [ ] Tests added or updated, `pytest` passes
- [ ] `ruff check . && ruff format --check .` passes
- [ ] CHANGELOG.md updated under "Unreleased"
