"""Parsing and schema validation for ``stack.toml``.

The schema is intentionally small and explicit so that a first-time contributor
can read it in a minute. Every rule here has a matching message that tells the
contributor exactly what to change.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised on Python 3.10 only
    import tomli as tomllib

CATEGORIES: dict[str, str] = {
    "ai": "Local AI and machine learning tools",
    "analytics": "Privacy-friendly web analytics",
    "automation": "Workflow automation",
    "cache": "Caches and key-value stores",
    "cms": "Websites and content management",
    "database": "Databases and database admin tools",
    "devtools": "Developer tools and code hosting",
    "email": "Email testing and delivery",
    "management": "Container and server management",
    "monitoring": "Monitoring, metrics and uptime",
    "productivity": "Files, sync and collaboration",
    "proxy": "Reverse proxies and TLS",
    "search": "Search engines",
    "security": "Passwords and secrets",
    "storage": "Object and file storage",
}

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TAG_RE = re.compile(r"^[a-z0-9]+(?:[-.][a-z0-9]+)*$")
ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
GITHUB_HANDLE_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
GENERATOR_RE = re.compile(r"^(alnum|hex|base64|urlsafe):(\d{1,3})$|^uuid$")
PROTOCOLS = ("tcp", "udp")

KNOWN_TOP_LEVEL = {
    "name",
    "description",
    "category",
    "tags",
    "upstream_docs",
    "maintained_by",
    "notes",
    "ports",
    "volumes",
    "healthcheck",
    "env",
}


class MetadataError(ValueError):
    """Raised when ``stack.toml`` cannot be parsed at all."""


@dataclass(frozen=True)
class Port:
    service: str
    host: int
    container: int
    bind: str = "127.0.0.1"
    protocol: str = "tcp"
    description: str = ""

    @property
    def public(self) -> bool:
        return self.bind in ("0.0.0.0", "::", "")


@dataclass(frozen=True)
class Volume:
    name: str
    description: str = ""


@dataclass(frozen=True)
class EnvVar:
    name: str
    description: str = ""
    secret: bool = False
    generate: str = ""
    default: str = ""
    required: bool = False


@dataclass
class Metadata:
    name: str
    description: str
    category: str
    tags: list[str]
    upstream_docs: str
    maintained_by: list[str]
    notes: str = ""
    ports: list[Port] = field(default_factory=list)
    volumes: list[Volume] = field(default_factory=list)
    healthcheck_services: list[str] = field(default_factory=list)
    healthcheck_exempt: dict[str, str] = field(default_factory=dict)
    env: dict[str, EnvVar] = field(default_factory=dict)

    @property
    def secrets(self) -> list[EnvVar]:
        return [v for v in self.env.values() if v.secret]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tags": list(self.tags),
            "upstream_docs": self.upstream_docs,
            "maintained_by": list(self.maintained_by),
            "notes": self.notes,
            "ports": [p.__dict__.copy() for p in self.ports],
            "volumes": [v.__dict__.copy() for v in self.volumes],
            "healthcheck": {"services": list(self.healthcheck_services), "exempt": dict(self.healthcheck_exempt)},
            "env": {k: v.__dict__.copy() for k, v in self.env.items()},
        }


def read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except FileNotFoundError as exc:
        raise MetadataError(f"{path.name} not found") from exc
    except tomllib.TOMLDecodeError as exc:
        raise MetadataError(f"{path.name} is not valid TOML: {exc}") from exc


def _str(data: dict[str, Any], key: str, problems: list[str], *, required: bool = True) -> str:
    value = data.get(key, "")
    if not isinstance(value, str):
        problems.append(f"'{key}' must be a string")
        return ""
    if required and not value.strip():
        problems.append(f"'{key}' is required")
    return value.strip()


def _str_list(data: dict[str, Any], key: str, problems: list[str]) -> list[str]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        problems.append(f"'{key}' must be a list of strings")
        return []
    return [x.strip() for x in value]


def parse_metadata(data: dict[str, Any]) -> tuple[Metadata, list[str]]:
    """Parse a decoded ``stack.toml`` and return the metadata plus schema problems.

    Parsing never raises for schema problems: the caller decides how to report
    them, which lets ``validate`` show every problem in one run.
    """

    problems: list[str] = []
    for key in sorted(set(data) - KNOWN_TOP_LEVEL):
        problems.append(f"unknown key '{key}' (allowed: {', '.join(sorted(KNOWN_TOP_LEVEL))})")

    name = _str(data, "name", problems)
    if name and not NAME_RE.match(name):
        problems.append(f"'name' must be lowercase kebab-case, got '{name}'")

    description = _str(data, "description", problems)
    if description and not (10 <= len(description) <= 160):
        problems.append("'description' should be 10-160 characters (it is shown in tables)")
    if description.endswith("."):
        problems.append("'description' should not end with a period")

    category = _str(data, "category", problems)
    if category and category not in CATEGORIES:
        problems.append(f"'category' must be one of: {', '.join(CATEGORIES)} (got '{category}')")

    tags = _str_list(data, "tags", problems)
    if not tags:
        problems.append("'tags' needs at least one tag")
    for tag in tags:
        if not TAG_RE.match(tag):
            problems.append(f"tag '{tag}' must be lowercase (letters, digits, '-' or '.')")
    if len(set(tags)) != len(tags):
        problems.append("'tags' contains duplicates")

    upstream = _str(data, "upstream_docs", problems)
    if upstream and not upstream.startswith("https://"):
        problems.append("'upstream_docs' must be an https:// URL")

    maintainers = _str_list(data, "maintained_by", problems)
    if not maintainers:
        problems.append("'maintained_by' needs at least one GitHub handle")
    for handle in maintainers:
        if not GITHUB_HANDLE_RE.match(handle.lstrip("@")):
            problems.append(f"'{handle}' is not a valid GitHub handle")

    notes = _str(data, "notes", problems, required=False)

    ports = _parse_ports(data.get("ports", []), problems)
    volumes = _parse_volumes(data.get("volumes", []), problems)
    hc_services, hc_exempt = _parse_healthcheck(data.get("healthcheck"), problems)
    env = _parse_env(data.get("env", {}), problems)

    meta = Metadata(
        name=name,
        description=description,
        category=category,
        tags=tags,
        upstream_docs=upstream,
        maintained_by=[m.lstrip("@") for m in maintainers],
        notes=notes,
        ports=ports,
        volumes=volumes,
        healthcheck_services=hc_services,
        healthcheck_exempt=hc_exempt,
        env=env,
    )
    return meta, problems


def _parse_ports(raw: Any, problems: list[str]) -> list[Port]:
    if not isinstance(raw, list):
        problems.append("'ports' must be an array of tables ([[ports]])")
        return []
    ports: list[Port] = []
    for i, item in enumerate(raw):
        where = f"ports[{i}]"
        if not isinstance(item, dict):
            problems.append(f"{where} must be a table")
            continue
        service = item.get("service")
        host = item.get("host")
        container = item.get("container")
        bind = item.get("bind", "127.0.0.1")
        protocol = item.get("protocol", "tcp")
        if not isinstance(service, str) or not service:
            problems.append(f"{where}.service is required")
            service = ""
        for label, value in (("host", host), ("container", container)):
            if not isinstance(value, int) or isinstance(value, bool) or not (1 <= value <= 65535):
                problems.append(f"{where}.{label} must be a port number between 1 and 65535")
        if not isinstance(bind, str):
            problems.append(f"{where}.bind must be a string such as '127.0.0.1' or '0.0.0.0'")
            bind = "127.0.0.1"
        if protocol not in PROTOCOLS:
            problems.append(f"{where}.protocol must be 'tcp' or 'udp'")
            protocol = "tcp"
        unknown = set(item) - {"service", "host", "container", "bind", "protocol", "description"}
        if unknown:
            problems.append(f"{where} has unknown keys: {', '.join(sorted(unknown))}")
        if isinstance(host, int) and isinstance(container, int):
            ports.append(Port(service, host, container, bind, protocol, str(item.get("description", ""))))
    return ports


def _parse_volumes(raw: Any, problems: list[str]) -> list[Volume]:
    if not isinstance(raw, list):
        problems.append("'volumes' must be an array of tables ([[volumes]])")
        return []
    volumes: list[Volume] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"]:
            problems.append(f"volumes[{i}] needs a 'name'")
            continue
        volumes.append(Volume(item["name"], str(item.get("description", ""))))
    return volumes


def _parse_healthcheck(raw: Any, problems: list[str]) -> tuple[list[str], dict[str, str]]:
    if raw is None:
        problems.append("'[healthcheck]' table is required (list the services that define a healthcheck)")
        return [], {}
    if not isinstance(raw, dict):
        problems.append("'healthcheck' must be a table")
        return [], {}
    services = _str_list(raw, "services", problems)
    exempt_raw = raw.get("exempt", {})
    exempt: dict[str, str] = {}
    if not isinstance(exempt_raw, dict):
        problems.append("'healthcheck.exempt' must be a table of service = \"reason\"")
    else:
        for service, reason in exempt_raw.items():
            if not isinstance(reason, str) or len(reason.strip()) < 10:
                problems.append(f"healthcheck.exempt.{service} needs a reason of at least 10 characters")
            else:
                exempt[service] = reason.strip()
    if not services and not exempt:
        problems.append("'healthcheck.services' must list at least one service")
    return services, exempt


def _parse_env(raw: Any, problems: list[str]) -> dict[str, EnvVar]:
    if not isinstance(raw, dict):
        problems.append("'env' must be a table of tables ([env.VAR_NAME])")
        return {}
    env: dict[str, EnvVar] = {}
    for name, spec in raw.items():
        where = f"env.{name}"
        if not ENV_NAME_RE.match(name):
            problems.append(f"{where}: variable names must be UPPER_SNAKE_CASE")
        if not isinstance(spec, dict):
            problems.append(f"{where} must be a table")
            continue
        unknown = set(spec) - {"description", "secret", "generate", "default", "required"}
        if unknown:
            problems.append(f"{where} has unknown keys: {', '.join(sorted(unknown))}")
        secret = spec.get("secret", False)
        if not isinstance(secret, bool):
            problems.append(f"{where}.secret must be true or false")
            secret = False
        generate = spec.get("generate", "")
        if not isinstance(generate, str):
            problems.append(f"{where}.generate must be a string such as 'alnum:32'")
            generate = ""
        if secret and not generate:
            generate = "alnum:32"
        if generate and not GENERATOR_RE.match(generate):
            problems.append(
                f"{where}.generate '{generate}' is invalid (use alnum:N, hex:N, base64:N, urlsafe:N or uuid)"
            )
        if generate and not secret:
            problems.append(f"{where}.generate is only allowed together with secret = true")
        default = spec.get("default", "")
        if not isinstance(default, (str, int)) or isinstance(default, bool):
            problems.append(f"{where}.default must be a string or number")
            default = ""
        if secret and default != "":
            problems.append(f"{where} is secret, so it must not have a default value")
        description = spec.get("description", "")
        if not isinstance(description, str) or not description.strip():
            problems.append(f"{where}.description is required")
            description = ""
        env[name] = EnvVar(
            name=name,
            description=description.strip(),
            secret=secret,
            generate=generate,
            default=str(default),
            required=bool(spec.get("required", secret)),
        )
    return env


def load_metadata(path: Path) -> tuple[Metadata, list[str]]:
    return parse_metadata(read_toml(path))
