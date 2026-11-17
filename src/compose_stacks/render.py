"""Text, JSON, Markdown and CI annotation output."""

from __future__ import annotations

import json
import shutil
import textwrap
from collections.abc import Sequence
from typing import Any

from compose_stacks.catalog import Stack
from compose_stacks.compose import parse_image
from compose_stacks.metadata import CATEGORIES
from compose_stacks.validate import ERROR, WARNING, Report

README_START = "<!-- stacks:start -->"
README_END = "<!-- stacks:end -->"


def table(rows: Sequence[Sequence[str]], headers: Sequence[str], max_width: int | None = None) -> str:
    """Render a plain-text table that fits the terminal (the last column is truncated)."""

    max_width = max_width or shutil.get_terminal_size((120, 20)).columns
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    fixed = sum(widths[:-1]) + 2 * (len(widths) - 1)
    widths[-1] = max(10, min(widths[-1], max_width - fixed))

    def fmt(row: Sequence[str]) -> str:
        cells = []
        for i, cell in enumerate(row):
            if i == len(row) - 1 and len(cell) > widths[i]:
                cell = cell[: widths[i] - 1] + "…"
            cells.append(cell.ljust(widths[i]) if i < len(row) - 1 else cell)
        return "  ".join(cells).rstrip()

    lines = [fmt(headers), fmt(["-" * w for w in widths])]
    lines.extend(fmt(r) for r in rows)
    return "\n".join(lines)


def stacks_table(stacks: Sequence[Stack], max_width: int | None = None) -> str:
    rows = []
    for stack in stacks:
        meta = stack.metadata
        if meta is None:
            rows.append([stack.name, "?", "?", f"error: {stack.load_error}"])
            continue
        rows.append([stack.name, meta.category, ",".join(meta.tags[:3]), meta.description])
    return table(rows, ["NAME", "CATEGORY", "TAGS", "DESCRIPTION"], max_width)


def stacks_json(stacks: Sequence[Stack]) -> str:
    return json.dumps([s.summary() for s in stacks], indent=2)


def show_stack(stack: Stack) -> str:
    meta = stack.metadata
    if meta is None:
        return f"{stack.name}: {stack.load_error}"
    out = [f"{meta.name} - {meta.description}", ""]
    out.append(f"  Category:     {meta.category} ({CATEGORIES.get(meta.category, '')})")
    out.append(f"  Tags:         {', '.join(meta.tags)}")
    out.append(f"  Services:     {', '.join(stack.services)}")
    out.append(f"  Images:       {', '.join(stack.images())}")
    out.append(f"  Docs:         {meta.upstream_docs}")
    out.append(f"  Maintainers:  {', '.join('@' + m for m in meta.maintained_by)}")
    out.append(f"  Path:         {stack.path}")
    if meta.ports:
        out.append("")
        out.append("  Ports:")
        for p in meta.ports:
            desc = f"  {p.description}" if p.description else ""
            out.append(f"    {p.bind}:{p.host} -> {p.service}:{p.container}/{p.protocol}{desc}")
    if meta.volumes:
        out.append("")
        out.append("  Volumes:")
        for v in meta.volumes:
            out.append(f"    {v.name}" + (f"  {v.description}" if v.description else ""))
    if meta.env:
        out.append("")
        out.append("  Environment:")
        for var in meta.env.values():
            flag = " [secret, auto-filled by init]" if var.secret else ""
            default = f" (default: {var.default})" if var.default and not var.secret else ""
            out.append(f"    {var.name}{flag}{default}")
            if var.description:
                out.extend("      " + line for line in textwrap.wrap(var.description, 70))
    if meta.notes:
        out.append("")
        out.append("  Notes:")
        out.extend("    " + line for line in textwrap.wrap(meta.notes, 74))
    out.append("")
    out.append(f"  Deploy: compose-stacks init {meta.name} ./{meta.name} && cd {meta.name} && docker compose up -d")
    return "\n".join(out)


def readme_table(stacks: Sequence[Stack], link_prefix: str = "stacks") -> str:
    """Markdown table grouped by category, used between the README markers."""

    lines = [
        f"**{len(stacks)} stacks** across {len({s.metadata.category for s in stacks if s.metadata})} categories.",
        "",
    ]
    lines.append("| Stack | Category | Description | Images |")
    lines.append("| --- | --- | --- | --- |")
    ordered = sorted(
        (s for s in stacks if s.metadata),
        key=lambda s: (s.metadata.category, s.name),  # type: ignore[union-attr]
    )
    for stack in ordered:
        meta = stack.metadata
        assert meta is not None
        # Image names without tags, so version bumps do not touch the README.
        repos = dict.fromkeys(parse_image(img).repository for img in stack.images())
        images = " ".join(f"`{repo}`" for repo in repos)
        desc = meta.description.replace("|", "\\|")
        lines.append(f"| [{stack.name}]({link_prefix}/{stack.name}/) | {meta.category} | {desc} | {images} |")
    return "\n".join(lines)


def replace_between_markers(text: str, content: str) -> str:
    start = text.find(README_START)
    end = text.find(README_END)
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"README must contain {README_START} and {README_END}")
    return text[: start + len(README_START)] + "\n" + content.strip() + "\n" + text[end:]


def report_text(report: Report, verbose: bool = False) -> str:
    out: list[str] = []
    by_stack: dict[str, list[Any]] = {}
    for issue in report.issues:
        by_stack.setdefault(issue.stack, []).append(issue)
    for name in report.checked:
        issues = by_stack.get(name, [])
        shown = [i for i in issues if verbose or i.level != "info"]
        errors = sum(1 for i in issues if i.level == ERROR)
        warnings = sum(1 for i in issues if i.level == WARNING)
        status = "FAIL" if errors else ("WARN" if warnings else "ok")
        out.append(f"{status:<4}  {name}")
        for issue in shown:
            where = f" [{issue.file}]" if issue.file else ""
            out.append(f"      {issue.level.upper():<7} {issue.code} {issue.message}{where}")
            if issue.hint and verbose:
                out.append(f"              hint: {issue.hint}")
    out.append("")
    out.append(
        f"{len(report.checked)} stack(s) checked: {len(report.errors)} error(s), {len(report.warnings)} warning(s)"
    )
    return "\n".join(out)


def report_github(report: Report, stacks_root: str = "stacks") -> str:
    """GitHub Actions workflow commands, so problems show up inline on pull requests."""

    lines = []
    for issue in report.issues:
        if issue.level == "info":
            continue
        kind = "error" if issue.level == ERROR else "warning"
        file = f"{stacks_root}/{issue.stack}/{issue.file}" if issue.file else f"{stacks_root}/{issue.stack}"
        message = issue.message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        lines.append(f"::{kind} file={file},title={issue.code}::{message}")
    lines.append(report_text(report))
    return "\n".join(lines)


def report_json(report: Report) -> str:
    return json.dumps(report.to_dict(), indent=2)
