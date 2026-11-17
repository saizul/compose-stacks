"""``init`` (deploy a stack into a folder) and ``new`` (start a new stack from the template)."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from compose_stacks.catalog import Stack, find_templates_dir
from compose_stacks.generators import generate
from compose_stacks.metadata import CATEGORIES, NAME_RE

_IGNORE = shutil.ignore_patterns(".env", "__pycache__", ".DS_Store")
_LINE_RE = re.compile(r"^(?P<prefix>\s*(?:export\s+)?)(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>.*)$")


class ScaffoldError(RuntimeError):
    """Raised when ``init`` or ``new`` cannot proceed safely."""


@dataclass
class InitResult:
    target: Path
    generated: list[str] = field(default_factory=list)
    overridden: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)


def render_env(
    stack: Stack,
    overrides: dict[str, str] | None = None,
    *,
    generate_secrets: bool = True,
    result: InitResult | None = None,
) -> str:
    """Render ``.env`` content from ``.env.example``.

    Comments and ordering are preserved. Secret variables declared in
    ``stack.toml`` are filled with fresh random values unless an override is
    given. Every other value keeps its example default.
    """

    overrides = dict(overrides or {})
    meta = stack.metadata
    env_meta = meta.env if meta else {}
    out_lines: list[str] = []
    seen: set[str] = set()
    for line in stack.env_example_text.splitlines():
        match = _LINE_RE.match(line)
        if not match:
            out_lines.append(line)
            continue
        key = match.group("key")
        value = match.group("value")
        seen.add(key)
        spec = env_meta.get(key)
        if key in overrides:
            value = overrides.pop(key)
            if result is not None:
                result.overridden.append(key)
        elif spec is not None and spec.secret and generate_secrets and not value.strip():
            value = generate(spec.generate or "alnum:32")
            if result is not None:
                result.generated.append(key)
        if spec is not None and spec.required and not value.strip() and result is not None:
            result.missing_required.append(key)
        out_lines.append(f"{match.group('prefix')}{key}={value}")
    if overrides:
        out_lines.append("")
        out_lines.append("# Added with --set")
        for key, value in overrides.items():
            seen.add(key)
            out_lines.append(f"{key}={value}")
            if result is not None:
                result.overridden.append(key)
    for key, spec in env_meta.items():
        if key not in seen and spec.secret and generate_secrets:
            out_lines.append(f"{key}={generate(spec.generate or 'alnum:32')}")
            if result is not None:
                result.generated.append(key)
    return "\n".join(out_lines).rstrip("\n") + "\n"


def init_stack(
    stack: Stack,
    target: Path,
    *,
    overrides: dict[str, str] | None = None,
    force: bool = False,
    generate_secrets: bool = True,
) -> InitResult:
    """Copy ``stack`` into ``target`` and write a ready-to-use ``.env``."""

    target = target.resolve()
    if target.exists() and not target.is_dir():
        raise ScaffoldError(f"{target} exists and is not a directory")
    if target.exists() and not force:
        clashes = [p.name for p in (target / "compose.yaml", target / ".env") if p.exists()]
        if clashes:
            raise ScaffoldError(
                f"{target} already contains {', '.join(clashes)}; use --force to overwrite (your .env will be replaced)"
            )
    if target == stack.path.resolve():
        raise ScaffoldError("refusing to initialise a stack inside its own source folder")

    shutil.copytree(stack.path, target, dirs_exist_ok=True, ignore=_IGNORE)
    result = InitResult(target=target)
    content = render_env(stack, overrides, generate_secrets=generate_secrets, result=result)
    env_path = target / ".env"
    fd = os.open(env_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(content)
    os.chmod(env_path, 0o600)
    return result


def parse_overrides(pairs: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ScaffoldError(f"--set expects NAME=value, got '{pair}'")
        overrides[key] = value
    return overrides


def new_stack(
    name: str, stacks_dir: Path, *, category: str = "devtools", maintainer: str = "your-github-handle"
) -> Path:
    """Create ``stacks/<name>`` from ``templates/stack`` with placeholders filled in."""

    if not NAME_RE.match(name):
        raise ScaffoldError(f"'{name}' is not a valid stack name (use lowercase kebab-case, e.g. 'my-app')")
    if category not in CATEGORIES:
        raise ScaffoldError(f"unknown category '{category}' (choose from: {', '.join(CATEGORIES)})")
    template_root = find_templates_dir()
    if template_root is None or not (template_root / "stack").is_dir():
        raise ScaffoldError("stack template not found; run this from a clone of the repository")
    dest = stacks_dir / name
    if dest.exists():
        raise ScaffoldError(f"{dest} already exists")
    shutil.copytree(template_root / "stack", dest, ignore=_IGNORE)
    replacements = {"__NAME__": name, "__CATEGORY__": category, "__MAINTAINER__": maintainer}
    for path in dest.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            for old, new in replacements.items():
                text = text.replace(old, new)
            path.write_text(text, encoding="utf-8")
    return dest
