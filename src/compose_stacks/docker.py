"""Optional ``docker compose config`` check.

The check runs against a throw-away ``.env`` file filled with generated values,
so it never touches a real deployment and never needs network access.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from compose_stacks.catalog import Stack
from compose_stacks.scaffold import render_env
from compose_stacks.validate import Report


def docker_compose_command() -> list[str] | None:
    """Return the command prefix for Compose v2, or ``None`` when it is not installed."""

    docker = shutil.which("docker")
    if docker:
        try:
            probe = subprocess.run(
                [docker, "compose", "version"], capture_output=True, text=True, timeout=30, check=False
            )
        except (OSError, subprocess.TimeoutExpired):
            probe = None
        if probe is not None and probe.returncode == 0:
            return [docker, "compose"]
    legacy = shutil.which("docker-compose")
    return [legacy] if legacy else None


def compose_config(stack: Stack, command: list[str], timeout: int = 60) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="compose-stacks-") as tmp:
        env_path = Path(tmp) / ".env"
        env_path.write_text(render_env(stack), encoding="utf-8")
        args = [
            *command,
            "--project-directory",
            str(stack.path),
            "--env-file",
            str(env_path),
            "-f",
            str(stack.path / "compose.yaml"),
            "config",
            "--quiet",
        ]
        try:
            proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, str(exc)
    output = (proc.stderr or proc.stdout).strip()
    return proc.returncode == 0, output


def docker_check(stack: Stack, report: Report, command: list[str] | None) -> None:
    if command is None:
        report.add("CS051", stack.name, "docker compose not found; skipped")
        return
    ok, output = compose_config(stack, command)
    if not ok:
        report.add("CS050", stack.name, output or "docker compose config failed", file="compose.yaml")
