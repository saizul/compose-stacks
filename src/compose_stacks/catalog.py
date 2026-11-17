"""Discovery and loading of stacks from a stacks directory."""

from __future__ import annotations

import difflib
import os
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

from compose_stacks.compose import ComposeError, interpolate, load_compose, parse_env_file, parse_image
from compose_stacks.metadata import Metadata, MetadataError, load_metadata

ENV_VAR = "COMPOSE_STACKS_DIR"
REQUIRED_FILES = ("compose.yaml", ".env.example", "README.md", "stack.toml")
_PACKAGE_DIR = Path(__file__).resolve().parent


class CatalogError(LookupError):
    """Raised when a stack or the stacks directory cannot be found."""


def find_stacks_dir(explicit: str | os.PathLike[str] | None = None) -> Path:
    """Locate the stacks directory.

    Order: explicit argument, ``$COMPOSE_STACKS_DIR``, the repository checkout
    (``<repo>/stacks`` for editable installs), then the copy bundled in the wheel.
    """

    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    elif os.environ.get(ENV_VAR):
        candidates.append(Path(os.environ[ENV_VAR]))
    else:
        candidates.append(_PACKAGE_DIR.parent.parent / "stacks")
        candidates.append(_PACKAGE_DIR / "stacks")
    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()
    raise CatalogError(f"stacks directory not found (looked in: {', '.join(str(c) for c in candidates)})")


def find_templates_dir() -> Path | None:
    for candidate in (_PACKAGE_DIR.parent.parent / "templates", _PACKAGE_DIR / "templates"):
        if candidate.is_dir():
            return candidate
    return None


@dataclass
class Stack:
    path: Path
    metadata: Metadata | None = None
    metadata_problems: list[str] = field(default_factory=list)
    load_error: str = ""

    @classmethod
    def load(cls, path: Path) -> Stack:
        stack = cls(path=path)
        try:
            stack.metadata, stack.metadata_problems = load_metadata(path / "stack.toml")
        except MetadataError as exc:
            stack.load_error = str(exc)
        return stack

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def ok(self) -> bool:
        return self.metadata is not None

    @cached_property
    def compose(self) -> dict[str, Any]:
        return load_compose(self.path / "compose.yaml")

    @property
    def compose_error(self) -> str:
        try:
            self.compose  # noqa: B018 - populate the cache
        except ComposeError as exc:
            return str(exc)
        return ""

    @property
    def services(self) -> list[str]:
        try:
            return list(self.compose.get("services", {}))
        except ComposeError:
            return []

    @property
    def env_example_text(self) -> str:
        path = self.path / ".env.example"
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    @property
    def env_defaults(self) -> dict[str, str]:
        return parse_env_file(self.env_example_text)

    def images(self) -> list[str]:
        out: list[str] = []
        try:
            services = self.compose.get("services", {})
        except ComposeError:
            return out
        env = self.env_defaults
        for svc in services.values():
            if isinstance(svc, dict) and isinstance(svc.get("image"), str):
                out.append(parse_image(interpolate(svc["image"], env)).raw)
        return out

    def readme(self) -> str:
        path = self.path / "README.md"
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def summary(self) -> dict[str, Any]:
        meta = self.metadata
        base: dict[str, Any] = {"name": self.name, "path": str(self.path)}
        if meta is None:
            base["error"] = self.load_error
            return base
        data = meta.to_dict()
        data["path"] = str(self.path)
        data["services"] = self.services
        data["images"] = self.images()
        return data


class Catalog:
    """All stacks found in a directory, keyed by folder name."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._stacks: dict[str, Stack] | None = None

    @classmethod
    def discover(cls, explicit: str | os.PathLike[str] | None = None) -> Catalog:
        return cls(find_stacks_dir(explicit))

    @property
    def stacks(self) -> dict[str, Stack]:
        if self._stacks is None:
            found: dict[str, Stack] = {}
            for child in sorted(self.root.iterdir()):
                if child.is_dir() and not child.name.startswith((".", "_")) and (child / "stack.toml").exists():
                    found[child.name] = Stack.load(child)
            self._stacks = found
        return self._stacks

    def __iter__(self):
        return iter(self.stacks.values())

    def __len__(self) -> int:
        return len(self.stacks)

    def get(self, name: str) -> Stack:
        try:
            return self.stacks[name]
        except KeyError:
            close = suggest(name, list(self.stacks))
            hint = f" Did you mean: {', '.join(close)}?" if close else ""
            raise CatalogError(f"no stack named '{name}'.{hint}") from None

    def filter(self, category: str | None = None, tags: list[str] | None = None) -> list[Stack]:
        result = []
        for stack in self:
            meta = stack.metadata
            if meta is None:
                continue
            if category and meta.category != category:
                continue
            if tags and not all(t in meta.tags for t in tags):
                continue
            result.append(stack)
        return result

    def search(self, term: str) -> list[tuple[int, Stack]]:
        """Rank stacks by how well they match ``term`` (name > tag > category > description > image)."""

        words = [w for w in term.lower().split() if w]
        scored: list[tuple[int, Stack]] = []
        for stack in self:
            meta = stack.metadata
            if meta is None or not words:
                continue
            score = 0
            for word in words:
                word_score = 0
                if word == stack.name:
                    word_score = 100
                elif word in stack.name:
                    word_score = 60
                if word in meta.tags:
                    word_score = max(word_score, 50)
                elif any(word in t for t in meta.tags):
                    word_score = max(word_score, 30)
                if word in meta.category:
                    word_score = max(word_score, 25)
                if word in meta.description.lower():
                    word_score = max(word_score, 20)
                if any(word in img.lower() for img in stack.images()):
                    word_score = max(word_score, 15)
                if word_score == 0:
                    break
                score += word_score
            else:
                scored.append((score, stack))
        scored.sort(key=lambda item: (-item[0], item[1].name))
        return scored


def suggest(name: str, choices: list[str], limit: int = 3) -> list[str]:
    return difflib.get_close_matches(name, choices, n=limit, cutoff=0.5)
