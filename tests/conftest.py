from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
STACKS_DIR = REPO_ROOT / "stacks"

COMPOSE = """\
services:
  app:
    image: example/app:1.2.3
    restart: unless-stopped
    environment:
      APP_SECRET: ${APP_SECRET:?required}
    ports:
      - "${BIND_ADDRESS:-127.0.0.1}:${APP_PORT:-8080}:80"
    volumes:
      - app_data:/data
    healthcheck:
      test: ["CMD", "true"]

volumes:
  app_data:
"""

ENV_EXAMPLE = """\
BIND_ADDRESS=127.0.0.1
APP_PORT=8080
# Generate: openssl rand -hex 32
APP_SECRET=
"""

STACK_TOML = """\
name = "demo"
description = "A demo stack used by the test-suite"
category = "devtools"
tags = ["demo", "test"]
upstream_docs = "https://example.org/docs"
maintained_by = ["saizul"]

[[ports]]
service = "app"
host = 8080
container = 80
description = "HTTP"

[[volumes]]
name = "app_data"

[healthcheck]
services = ["app"]

[env.BIND_ADDRESS]
description = "Bind address"
default = "127.0.0.1"

[env.APP_PORT]
description = "Port"
default = "8080"

[env.APP_SECRET]
description = "Secret"
secret = true
generate = "hex:16"
"""

README = """\
# Demo

## Quick start

Run it.

## Configuration

Configure it.
"""


def write_stack(root: Path, name: str = "demo", **overrides: str) -> Path:
    """Create a valid stack folder; pass compose=..., env=..., toml=..., readme=... to replace files."""

    path = root / name
    path.mkdir(parents=True, exist_ok=True)
    files = {
        "compose.yaml": overrides.get("compose", COMPOSE),
        ".env.example": overrides.get("env", ENV_EXAMPLE),
        "stack.toml": overrides.get("toml", STACK_TOML.replace('name = "demo"', f'name = "{name}"')),
        "README.md": overrides.get("readme", README),
    }
    for filename, content in files.items():
        if content is None:
            continue
        (path / filename).write_text(textwrap.dedent(content), encoding="utf-8")
    return path


@pytest.fixture
def stacks_root(tmp_path: Path) -> Path:
    root = tmp_path / "stacks"
    root.mkdir()
    return root


@pytest.fixture
def demo_stack(stacks_root: Path) -> Path:
    return write_stack(stacks_root)
