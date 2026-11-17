"""Small, dependency-light helpers for reading Compose files and ``.env`` files.

This is not a full Compose implementation. It understands exactly what the
validator needs: variable interpolation, image references, port mappings,
healthchecks and environment blocks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_VAR_RE = re.compile(
    r"""
    \$(?:
        (?P<escaped>\$)                                   # $$ -> literal $
      | \{(?P<braced>[A-Za-z_][A-Za-z0-9_]*)
          (?:(?P<op>:?[-?+])(?P<arg>[^}]*))?\}            # ${VAR}, ${VAR:-x}, ${VAR?err}
      | (?P<plain>[A-Za-z_][A-Za-z0-9_]*)                 # $VAR
    )
    """,
    re.VERBOSE,
)


class ComposeError(ValueError):
    """Raised when a Compose file cannot be read."""


def load_compose(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ComposeError(f"{path.name} not found") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ComposeError(f"{path.name} is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ComposeError(f"{path.name} must be a YAML mapping")
    services = data.get("services")
    if not isinstance(services, dict) or not services:
        raise ComposeError(f"{path.name} must define at least one service under 'services'")
    return data


def parse_env_file(text: str) -> dict[str, str]:
    """Parse ``KEY=value`` lines the way ``docker compose`` reads ``.env`` files."""

    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        values[key] = value
    return values


def env_file_order(text: str) -> list[str]:
    return [k for k in (ln.split("=", 1)[0].strip() for ln in text.splitlines() if "=" in ln) if k and k[0] != "#"]


def referenced_variables(value: Any) -> set[str]:
    """Return every variable name referenced anywhere inside ``value``."""

    found: set[str] = set()
    for text in _walk_strings(value):
        for match in _VAR_RE.finditer(text):
            name = match.group("braced") or match.group("plain")
            if name:
                found.add(name)
    return found


def variables_with_defaults(value: Any) -> set[str]:
    found: set[str] = set()
    for text in _walk_strings(value):
        for match in _VAR_RE.finditer(text):
            if match.group("braced") and match.group("op") in (":-", "-"):
                found.add(match.group("braced"))
    return found


def _walk_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str):
                yield k
            yield from _walk_strings(v)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)


def interpolate(text: str, env: dict[str, str]) -> str:
    """Interpolate ``text`` with Compose semantics (missing variables become empty)."""

    def repl(match: re.Match[str]) -> str:
        if match.group("escaped"):
            return "$"
        name = match.group("braced") or match.group("plain")
        op = match.group("op")
        arg = match.group("arg") or ""
        value = env.get(name)
        if op == ":-":
            return value if value else interpolate(arg, env)
        if op == "-":
            return value if value is not None else interpolate(arg, env)
        if op == ":+":
            return interpolate(arg, env) if value else ""
        if op == "+":
            return interpolate(arg, env) if value is not None else ""
        return value or ""

    return _VAR_RE.sub(repl, text)


@dataclass(frozen=True)
class ImageRef:
    raw: str
    repository: str
    tag: str
    digest: str

    @property
    def pinned(self) -> bool:
        return bool(self.digest) or (bool(self.tag) and self.tag not in FLOATING_TAGS)


FLOATING_TAGS = frozenset(
    {"latest", "stable", "main", "master", "nightly", "dev", "develop", "edge", "rolling", "release", "beta", "current"}
)


def parse_image(ref: str) -> ImageRef:
    raw = ref.strip()
    rest, digest = raw, ""
    if "@" in rest:
        rest, digest = rest.split("@", 1)
    last = rest.rsplit("/", 1)[-1]
    tag = ""
    if ":" in last:
        repo_part, tag = rest.rsplit(":", 1)
    else:
        repo_part = rest
    return ImageRef(raw=raw, repository=repo_part, tag=tag, digest=digest)


def is_major_only_tag(tag: str) -> bool:
    """True for tags like ``18`` or ``v3`` or ``18-alpine`` that float across minor releases."""

    return bool(re.fullmatch(r"v?\d+(?:-[a-z][a-z0-9.]*)?", tag))


@dataclass(frozen=True)
class PortMapping:
    host_ip: str
    published: str
    target: str
    protocol: str
    raw: str

    @property
    def is_published(self) -> bool:
        return bool(self.published)


_PORT_NUM = r"\d{1,5}(?:-\d{1,5})?"
_SHORT_PORT_RE = re.compile(
    rf"""^
    (?:(?P<ip>\[[0-9a-fA-F:.]+\]|[0-9.]+|[a-zA-Z0-9.-]+):)??
    (?:(?P<published>{_PORT_NUM}):)?
    (?P<target>{_PORT_NUM})
    (?:/(?P<proto>tcp|udp|sctp))?$""",
    re.VERBOSE,
)


def parse_port(spec: Any) -> PortMapping:
    """Parse short (``"127.0.0.1:8080:80/tcp"``) or long (mapping) port syntax.

    Raises ``ValueError`` with a readable message when the syntax is invalid.
    """

    if isinstance(spec, int) and not isinstance(spec, bool):
        spec = str(spec)
    if isinstance(spec, dict):
        target = spec.get("target")
        if target is None:
            raise ValueError("long port syntax needs a 'target'")
        published = spec.get("published", "")
        return PortMapping(
            host_ip=str(spec.get("host_ip", "")),
            published=str(published) if published not in (None, "") else "",
            target=str(target),
            protocol=str(spec.get("protocol", "tcp")),
            raw=str(spec),
        )
    if not isinstance(spec, str):
        raise ValueError(f"unsupported port entry: {spec!r}")
    match = _SHORT_PORT_RE.match(spec.strip())
    if not match:
        raise ValueError(f"'{spec}' is not a valid port mapping (expected [IP:]HOST:CONTAINER[/PROTO])")
    ip = (match.group("ip") or "").strip("[]")
    for part in (match.group("published"), match.group("target")):
        if part:
            for num in part.split("-"):
                if not 0 < int(num) <= 65535:
                    raise ValueError(f"port {num} in '{spec}' is out of range")
    return PortMapping(
        host_ip=ip,
        published=match.group("published") or "",
        target=match.group("target"),
        protocol=match.group("proto") or "tcp",
        raw=spec,
    )


def environment_items(service: dict[str, Any]) -> list[tuple[str, str | None]]:
    """Return ``(key, value)`` pairs from a service ``environment`` block (list or mapping)."""

    env = service.get("environment")
    items: list[tuple[str, str | None]] = []
    if isinstance(env, dict):
        for key, value in env.items():
            items.append((str(key), None if value is None else str(value)))
    elif isinstance(env, list):
        for entry in env:
            text = str(entry)
            if "=" in text:
                key, _, value = text.partition("=")
                items.append((key, value))
            else:
                items.append((text, None))
    return items


def has_healthcheck(service: dict[str, Any]) -> bool:
    hc = service.get("healthcheck")
    if not isinstance(hc, dict) or hc.get("disable") is True:
        return False
    test = hc.get("test")
    if isinstance(test, list):
        return bool(test) and test[0] != "NONE"
    return isinstance(test, str) and bool(test.strip())
