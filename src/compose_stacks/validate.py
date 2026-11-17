"""Offline validation of a stack folder.

Each rule has a stable code (``CS0xx``) so that contributors can search the docs
for it and so that CI annotations stay meaningful across releases. The full list
lives in ``RULES`` and is rendered in CONTRIBUTING.md.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from compose_stacks.catalog import REQUIRED_FILES, Stack
from compose_stacks.compose import (
    ComposeError,
    environment_items,
    has_healthcheck,
    interpolate,
    is_major_only_tag,
    parse_env_file,
    parse_image,
    parse_port,
    referenced_variables,
    variables_with_defaults,
)

ERROR = "error"
WARNING = "warning"
INFO = "info"

RULES: dict[str, tuple[str, str]] = {
    "CS001": (ERROR, "A required file is missing (compose.yaml, .env.example, README.md, stack.toml)"),
    "CS002": (ERROR, "stack.toml cannot be parsed"),
    "CS003": (ERROR, "stack.toml does not match the schema"),
    "CS004": (ERROR, "stack.toml 'name' must equal the folder name"),
    "CS005": (WARNING, "README.md is missing a recommended section"),
    "CS010": (ERROR, "compose.yaml cannot be parsed"),
    "CS011": (WARNING, "The top-level 'version' key is obsolete"),
    "CS012": (ERROR, "Every service must use a published image (no 'build')"),
    "CS013": (ERROR, "Image tags must be pinned (no missing tag, no :latest or other floating tags)"),
    "CS014": (WARNING, "Major-only tags (for example postgres:18) float across minor releases"),
    "CS015": (ERROR, "Every service needs a healthcheck or a documented exemption"),
    "CS016": (ERROR, "healthcheck.services in stack.toml does not match compose.yaml"),
    "CS017": (WARNING, "Services should set a restart policy"),
    "CS018": (WARNING, "container_name prevents running a stack twice on one host"),
    "CS019": (WARNING, "privileged containers need a very good reason"),
    "CS020": (ERROR, "Invalid port mapping syntax"),
    "CS021": (ERROR, "Port binding does not match stack.toml (127.0.0.1 is the default)"),
    "CS022": (ERROR, "Published ports in compose.yaml and stack.toml must match"),
    "CS030": (ERROR, "A volume listed in stack.toml is not declared in compose.yaml"),
    "CS031": (WARNING, "A named volume in compose.yaml is not documented in stack.toml"),
    "CS040": (ERROR, "compose.yaml uses a variable that .env.example does not define"),
    "CS041": (ERROR, "A variable from stack.toml is missing in .env.example"),
    "CS042": (ERROR, "Secret variables must be empty in .env.example"),
    "CS043": (ERROR, "Hardcoded secret value in compose.yaml"),
    "CS044": (ERROR, "Something that looks like a real credential was found in a stack file"),
    "CS045": (WARNING, "A variable in .env.example is not described in stack.toml"),
    "CS046": (WARNING, "Secret variables should carry a generation hint comment in .env.example"),
    "CS047": (WARNING, "A variable looks secret but is not marked secret = true in stack.toml"),
    "CS048": (WARNING, "The default in stack.toml differs from the value in .env.example"),
    "CS050": (ERROR, "docker compose config failed"),
    "CS051": (INFO, "docker is not available, the docker compose config check was skipped"),
}

SECRET_NAME_RE = re.compile(
    r"(PASSWORD|PASSWD|SECRET|TOKEN|API_KEY|PRIVATE_KEY|ACCESS_KEY|ENCRYPTION_KEY|MASTER_KEY|_KEY$|_PASS$|SALT)"
)
NOT_SECRET_SUFFIXES = ("_FILE", "_PATH", "_LENGTH", "_ALGORITHM", "_ALGO", "_EXPIRY", "_TTL", "_HEADER")
HARMLESS_VALUES = frozenset({"", "yes", "no", "true", "false", "0", "1", "on", "off", "none", "null"})
CREDENTIAL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("credentials in a URL", re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:/@${}]+:(?!\$)[^\s@/]+@[^\s]+")),
]
README_SECTIONS = ("Quick start", "Configuration")
TEXT_SUFFIXES = {".yaml", ".yml", ".toml", ".md", ".example", ".conf", ".json", ".txt", ".env", ".ini", ""}


@dataclass(frozen=True)
class Issue:
    code: str
    level: str
    stack: str
    message: str
    file: str = ""
    hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Report:
    issues: list[Issue] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)

    def add(self, code: str, stack: str, message: str, *, file: str = "", hint: str = "", level: str = "") -> None:
        self.issues.append(Issue(code, level or RULES[code][0], stack, message, file, hint))

    def extend(self, other: Report) -> None:
        self.issues.extend(other.issues)
        self.checked.extend(other.checked)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == ERROR]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == WARNING]

    def ok(self, strict: bool = False) -> bool:
        return not self.errors and not (strict and self.warnings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checked": self.checked,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "issues": [i.to_dict() for i in self.issues],
        }


def looks_secret(name: str) -> bool:
    upper = name.upper()
    return bool(SECRET_NAME_RE.search(upper)) and not upper.endswith(NOT_SECRET_SUFFIXES)


def validate_stack(stack: Stack) -> Report:
    """Run every offline rule against one stack folder."""

    report = Report(checked=[stack.name])
    name = stack.name

    missing = [f for f in REQUIRED_FILES if not (stack.path / f).is_file()]
    for f in missing:
        report.add("CS001", name, f"missing required file {f}", file=f, hint="copy it from templates/stack/")

    if stack.load_error:
        report.add("CS002", name, stack.load_error, file="stack.toml")
    for problem in stack.metadata_problems:
        report.add("CS003", name, problem, file="stack.toml")
    meta = stack.metadata
    if meta is not None and meta.name and meta.name != stack.path.name:
        report.add("CS004", name, f"name is '{meta.name}' but the folder is '{stack.path.name}'", file="stack.toml")

    _check_readme(stack, report)
    _check_credentials(stack, report)

    if "compose.yaml" in missing:
        return report
    try:
        compose = stack.compose
    except ComposeError as exc:
        report.add("CS010", name, str(exc), file="compose.yaml")
        return report

    env_text = stack.env_example_text
    env_defaults = parse_env_file(env_text)
    services: dict[str, Any] = compose.get("services", {})

    if "version" in compose:
        report.add("CS011", name, "remove the top-level 'version' key", file="compose.yaml")

    _check_services(stack, services, env_defaults, report)
    _check_ports(stack, services, env_defaults, report)
    _check_volumes(stack, compose, report)
    _check_env(stack, compose, services, env_text, env_defaults, report)
    return report


def _check_readme(stack: Stack, report: Report) -> None:
    text = stack.readme()
    if not text:
        return
    headings = {m.group(1).strip().lower() for m in re.finditer(r"^#{2,3}\s+(.+?)\s*#*$", text, re.MULTILINE)}
    for section in README_SECTIONS:
        if section.lower() not in headings:
            report.add("CS005", stack.name, f"README.md has no '## {section}' section", file="README.md")


def _check_credentials(stack: Stack, report: Report) -> None:
    for path in sorted(stack.path.rglob("*")):
        if not path.is_file() or path.name == ".env" or path.suffix not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(stack.path).as_posix()
        for lineno, line in enumerate(text.splitlines(), start=1):
            for label, pattern in CREDENTIAL_PATTERNS:
                if pattern.search(line):
                    report.add(
                        "CS044",
                        stack.name,
                        f"{rel}:{lineno} looks like a {label}",
                        file=rel,
                        hint="use an environment variable and leave the value empty in .env.example",
                    )


def _check_services(stack: Stack, services: dict[str, Any], env: dict[str, str], report: Report) -> None:
    name = stack.name
    meta = stack.metadata
    exempt = meta.healthcheck_exempt if meta else {}
    declared_hc = set(meta.healthcheck_services) if meta else set()

    for svc_name, svc in services.items():
        if not isinstance(svc, dict):
            report.add("CS010", name, f"service '{svc_name}' must be a mapping", file="compose.yaml")
            continue
        image = svc.get("image")
        if "build" in svc or not isinstance(image, str):
            report.add("CS012", name, f"service '{svc_name}' must set 'image' and must not use 'build'")
        else:
            ref = parse_image(interpolate(image, env))
            if not ref.pinned:
                shown = ref.tag or "(no tag)"
                report.add(
                    "CS013",
                    name,
                    f"service '{svc_name}' uses {ref.repository}:{shown}",
                    file="compose.yaml",
                    hint="pin a specific version, for example postgres:18.7-alpine",
                )
            elif ref.tag and not ref.digest and is_major_only_tag(ref.tag):
                report.add("CS014", name, f"service '{svc_name}' uses major-only tag '{ref.tag}'", file="compose.yaml")

        if has_healthcheck(svc):
            if svc_name in exempt:
                report.add(
                    "CS016",
                    name,
                    f"service '{svc_name}' has a healthcheck but is listed in healthcheck.exempt",
                    file="stack.toml",
                    level=WARNING,
                )
        elif svc_name not in exempt:
            report.add(
                "CS015",
                name,
                f"service '{svc_name}' has no healthcheck",
                file="compose.yaml",
                hint='add a healthcheck, or add healthcheck.exempt.<service> = "reason" to stack.toml',
            )

        restart = svc.get("restart")
        if restart in (None, "no", False):
            report.add("CS017", name, f"service '{svc_name}' has no restart policy", hint="use restart: unless-stopped")
        if "container_name" in svc:
            report.add("CS018", name, f"service '{svc_name}' sets container_name", file="compose.yaml")
        if svc.get("privileged") is True:
            report.add("CS019", name, f"service '{svc_name}' runs privileged", file="compose.yaml")

    if meta is not None:
        for svc_name in sorted(declared_hc - set(services)):
            report.add("CS016", name, f"healthcheck.services lists unknown service '{svc_name}'", file="stack.toml")
        for svc_name in sorted(declared_hc & set(services)):
            if isinstance(services[svc_name], dict) and not has_healthcheck(services[svc_name]):
                report.add(
                    "CS016",
                    name,
                    f"healthcheck.services lists '{svc_name}' but it has no healthcheck",
                    file="stack.toml",
                )
        for svc_name in sorted(set(services) - declared_hc - set(exempt)):
            if isinstance(services[svc_name], dict) and has_healthcheck(services[svc_name]):
                report.add("CS016", name, f"add '{svc_name}' to healthcheck.services in stack.toml", file="stack.toml")
        for svc_name in sorted(set(exempt) - set(services)):
            report.add("CS016", name, f"healthcheck.exempt lists unknown service '{svc_name}'", file="stack.toml")


def _check_ports(stack: Stack, services: dict[str, Any], env: dict[str, str], report: Report) -> None:
    name = stack.name
    meta = stack.metadata
    published: list[tuple[str, str, str, str, str]] = []
    for svc_name, svc in services.items():
        if not isinstance(svc, dict):
            continue
        for entry in svc.get("ports", []) or []:
            spec = interpolate(entry, env) if isinstance(entry, str) else entry
            try:
                mapping = parse_port(spec)
            except ValueError as exc:
                report.add("CS020", name, f"service '{svc_name}': {exc}", file="compose.yaml")
                continue
            if mapping.is_published:
                published.append((svc_name, mapping.host_ip, mapping.published, mapping.target, mapping.protocol))
            else:
                report.add(
                    "CS020",
                    name,
                    f"service '{svc_name}' exposes '{mapping.raw}' on a random host port; set an explicit host port",
                    file="compose.yaml",
                    level=WARNING,
                )
    if meta is None:
        return

    documented = {(p.service, str(p.host), str(p.container), p.protocol): p for p in meta.ports}
    seen: set[tuple[str, str, str, str]] = set()
    for svc_name, host_ip, host, target, proto in published:
        key = (svc_name, host, target, proto)
        port = documented.get(key)
        if port is None:
            report.add(
                "CS022",
                name,
                f"service '{svc_name}' publishes {host}:{target}/{proto} without a matching [[ports]] entry",
                file="stack.toml",
            )
            continue
        seen.add(key)
        actual_public = host_ip in ("", "0.0.0.0", "::")
        if actual_public and not port.public:
            report.add(
                "CS021",
                name,
                f"service '{svc_name}' publishes {host} on all interfaces",
                file="compose.yaml",
                hint='prefix the mapping with ${BIND_ADDRESS:-127.0.0.1}: or set bind = "0.0.0.0" in stack.toml',
            )
        elif not actual_public and port.public:
            report.add(
                "CS021",
                name,
                f"stack.toml says {host} is public but compose.yaml binds it to {host_ip}",
                file="stack.toml",
            )
        elif not actual_public and host_ip != port.bind:
            report.add(
                "CS021", name, f"port {host} binds to {host_ip} but stack.toml says {port.bind}", file="stack.toml"
            )
    for key in sorted(set(documented) - seen):
        svc_name, host, target, proto = key
        report.add(
            "CS022",
            name,
            f"stack.toml documents {svc_name} {host}:{target}/{proto} but compose.yaml does not publish it",
            file="stack.toml",
        )


def _check_volumes(stack: Stack, compose: dict[str, Any], report: Report) -> None:
    meta = stack.metadata
    if meta is None:
        return
    declared = set((compose.get("volumes") or {}).keys())
    documented = {v.name for v in meta.volumes}
    for vol in sorted(documented - declared):
        report.add(
            "CS030", stack.name, f"volume '{vol}' is not declared under top-level 'volumes'", file="compose.yaml"
        )
    for vol in sorted(declared - documented):
        report.add("CS031", stack.name, f'add [[volumes]] name = "{vol}" to stack.toml', file="stack.toml")


def _check_env(
    stack: Stack,
    compose: dict[str, Any],
    services: dict[str, Any],
    env_text: str,
    env_defaults: dict[str, str],
    report: Report,
) -> None:
    name = stack.name
    meta = stack.metadata
    referenced = referenced_variables(compose)
    defaulted = variables_with_defaults(compose)
    for var in sorted(referenced - set(env_defaults) - defaulted):
        report.add(
            "CS040",
            name,
            f"${{{var}}} is used in compose.yaml but not defined in .env.example",
            file=".env.example",
        )

    for svc_name, svc in services.items():
        if not isinstance(svc, dict):
            continue
        for key, value in environment_items(svc):
            if value is None or not looks_secret(key):
                continue
            if "$" in value or value.strip().lower() in HARMLESS_VALUES:
                continue
            report.add(
                "CS043",
                name,
                f"service '{svc_name}' sets {key} to a literal value",
                file="compose.yaml",
                hint=f"use {key}: ${{{key}}} and add {key}= to .env.example",
            )

    if meta is None:
        return
    lines = env_text.splitlines()
    for var in meta.env.values():
        if var.name not in env_defaults:
            report.add("CS041", name, f"{var.name} is described in stack.toml but missing in .env.example")
            continue
        if var.secret:
            if env_defaults[var.name]:
                report.add(
                    "CS042",
                    name,
                    f"{var.name} is secret but has a value in .env.example",
                    file=".env.example",
                    hint="leave it empty; compose-stacks init fills it with a random value",
                )
            if not _has_hint(lines, var.name):
                report.add(
                    "CS046",
                    name,
                    f"add a comment above {var.name} such as '# Generate: openssl rand -hex 32'",
                    file=".env.example",
                )
    for var in sorted(set(env_defaults) - set(meta.env)):
        report.add("CS045", name, f"describe {var} under [env.{var}] in stack.toml", file="stack.toml")
    for var in sorted(set(env_defaults) & set(meta.env)):
        spec = meta.env[var]
        if looks_secret(var) and not spec.secret:
            report.add("CS047", name, f"{var} looks like a secret; set secret = true", file="stack.toml")
        if not spec.secret and spec.default != env_defaults[var]:
            report.add(
                "CS048",
                name,
                f"{var}: stack.toml default is '{spec.default}' but .env.example has '{env_defaults[var]}'",
                file="stack.toml",
            )


def _has_hint(lines: list[str], var: str) -> bool:
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{var}="):
            for prev in reversed(lines[max(0, i - 3) : i]):
                text = prev.strip().lower()
                if not text.startswith("#"):
                    break
                if "openssl" in text or "generate" in text or "compose-stacks init" in text:
                    return True
            return False
    return False
