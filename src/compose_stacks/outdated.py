"""``outdated``: compare a deployed stack folder with the library version it came from."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from compose_stacks.catalog import Catalog, CatalogError, Stack
from compose_stacks.compose import ComposeError, interpolate, load_compose, parse_env_file
from compose_stacks.metadata import MetadataError, read_toml
from compose_stacks.scaffold import ScaffoldError


@dataclass(frozen=True)
class ImageChange:
    service: str
    deployed: str | None  # None: the service is new in the library
    library: str | None  # None: the service is not in the library (removed or your own)

    @property
    def kind(self) -> str:
        if self.deployed is None:
            return "added"
        if self.library is None:
            return "extra"
        return "changed"

    def to_dict(self) -> dict[str, Any]:
        return {"service": self.service, "change": self.kind, "deployed": self.deployed, "library": self.library}


@dataclass
class OutdatedReport:
    directory: Path
    stack: str
    images: list[ImageChange] = field(default_factory=list)
    missing_env: list[str] = field(default_factory=list)
    up_to_date: list[str] = field(default_factory=list)

    @property
    def outdated(self) -> bool:
        return any(c.kind != "extra" for c in self.images) or bool(self.missing_env)

    def to_dict(self) -> dict[str, Any]:
        return {
            "directory": str(self.directory),
            "stack": self.stack,
            "outdated": self.outdated,
            "images": [c.to_dict() for c in self.images],
            "missing_env": self.missing_env,
            "up_to_date": self.up_to_date,
        }


def detect_stack_name(directory: Path) -> str:
    """The library stack a folder was created from: ``name`` in its ``stack.toml``, else the folder name."""

    meta = directory / "stack.toml"
    if meta.is_file():
        try:
            data = read_toml(meta)
        except (OSError, MetadataError) as exc:
            raise ScaffoldError(f"{meta}: {exc}; pass --stack NAME") from exc
        name = data.get("name")
        if isinstance(name, str) and name:
            return name
    return directory.resolve().name


def _service_images(compose: dict[str, Any], env: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    services = compose.get("services") or {}
    if not isinstance(services, dict):
        return out
    for name, svc in services.items():
        if isinstance(svc, dict) and isinstance(svc.get("image"), str):
            out[str(name)] = interpolate(svc["image"], env).strip()
    return out


def compare_deployment(directory: Path, stack: Stack) -> OutdatedReport:
    """Compare image tags and ``.env`` variables of ``directory`` with ``stack``."""

    directory = directory.resolve()
    compose_path = directory / "compose.yaml"
    if not compose_path.is_file():
        raise ScaffoldError(f"{directory} has no compose.yaml")
    try:
        deployed_compose = load_compose(compose_path)
    except ComposeError as exc:
        raise ScaffoldError(str(exc)) from exc
    env_path = directory / ".env"
    deployed_env_text = env_path.read_text(encoding="utf-8") if env_path.is_file() else ""
    deployed_env = parse_env_file(deployed_env_text)
    library_env = stack.env_defaults

    # Images are compared after interpolation, so tags set through variables count too: the deployed side
    # uses the folder's .env, the library side the defaults from its .env.example.
    deployed = _service_images(deployed_compose, {**library_env, **deployed_env})
    try:
        library = _service_images(stack.compose, library_env)
    except ComposeError as exc:
        raise ScaffoldError(f"library stack {stack.name}: {exc}") from exc

    report = OutdatedReport(directory=directory, stack=stack.name)
    for service in sorted(set(deployed) | set(library)):
        old, new = deployed.get(service), library.get(service)
        if old == new:
            report.up_to_date.append(service)
        else:
            report.images.append(ImageChange(service, old, new))
    if env_path.is_file():
        report.missing_env = [key for key in library_env if key not in deployed_env]
    return report


def check_directory(directory: Path, catalog: Catalog, stack_name: str | None = None) -> OutdatedReport:
    name = stack_name or detect_stack_name(directory)
    try:
        stack = catalog.get(name)
    except CatalogError as exc:
        raise ScaffoldError(f"{directory}: {exc}; pass --stack NAME if the folder was renamed") from exc
    return compare_deployment(directory, stack)


def render_text(reports: list[OutdatedReport]) -> str:
    lines: list[str] = []
    for report in reports:
        state = "outdated" if report.outdated else "up to date"
        lines.append(f"{report.directory} ({report.stack}): {state}")
        for change in report.images:
            if change.kind == "changed":
                lines.append(f"  {change.service}: {change.deployed} -> {change.library}")
            elif change.kind == "added":
                lines.append(f"  {change.service}: new service in the library ({change.library})")
            else:
                lines.append(f"  {change.service}: not in the library ({change.deployed}), left alone")
        if report.missing_env:
            lines.append(f"  .env is missing: {', '.join(report.missing_env)} (see .env.example in the library)")
    if any(r.outdated for r in reports):
        lines.append("")
        lines.append("Update the image tags in compose.yaml (compose-stacks show NAME --compose), add missing")
        lines.append(
            "variables to .env, read the upstream release notes, then: docker compose pull && docker compose up -d"
        )
    return "\n".join(lines)


def render_json(reports: list[OutdatedReport]) -> str:
    return json.dumps([r.to_dict() for r in reports], indent=2)
