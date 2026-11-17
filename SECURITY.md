# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | yes |

Stacks are maintained on the `main` branch; always use the latest version of a
stack before reporting an issue.

## What counts as a vulnerability

- A stack that exposes a service, admin UI or database on a public interface by default
- A stack that ships a default or hardcoded password, key or token
- A pinned image with a known critical vulnerability that has a fixed upstream release
- A bug in the CLI that leaks generated secrets (for example world-readable `.env` files)
- Anything in the CLI that could execute untrusted input

Vulnerabilities in the upstream applications themselves should go to their
own projects. Please still tell us if a stack needs a version bump.

## Reporting

Please **do not** open a public issue. Use
[GitHub private vulnerability reporting](https://github.com/saizul/compose-stacks/security/advisories/new)
and include the stack or command, the impact and steps to reproduce.

You will get a reply within 5 working days. Fixes are released as soon as
possible and credited in the changelog unless you prefer otherwise.

## Hardening tips for users

- Keep `BIND_ADDRESS=127.0.0.1` and put a TLS reverse proxy (the `traefik` or
  `caddy` stack) in front of web UIs.
- Never commit `.env`. Back it up separately and securely.
- Limit stacks that mount the Docker socket.
- Update images regularly and read the upstream release notes.
