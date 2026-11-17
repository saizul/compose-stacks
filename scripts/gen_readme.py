#!/usr/bin/env python3
"""Rebuild the stack table in README.md from every stacks/*/stack.toml.

Usage:
    python scripts/gen_readme.py           # rewrite README.md in place
    python scripts/gen_readme.py --check   # exit 1 if README.md is out of date (used in CI)
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from compose_stacks.catalog import Catalog  # noqa: E402
from compose_stacks.render import readme_table, replace_between_markers  # noqa: E402


def build(readme: Path, stacks_dir: Path) -> tuple[str, str]:
    current = readme.read_text(encoding="utf-8")
    catalog = Catalog(stacks_dir)
    updated = replace_between_markers(current, readme_table(list(catalog)))
    return current, updated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="only check, do not write")
    parser.add_argument("--readme", type=Path, default=ROOT / "README.md")
    parser.add_argument("--stacks-dir", type=Path, default=ROOT / "stacks")
    args = parser.parse_args(argv)

    current, updated = build(args.readme, args.stacks_dir)
    if current == updated:
        print("README.md stack table is up to date.")
        return 0
    if args.check:
        diff = difflib.unified_diff(
            current.splitlines(), updated.splitlines(), "README.md", "README.md (expected)", lineterm=""
        )
        print("\n".join(diff))
        print("\nREADME.md is out of date. Run: python scripts/gen_readme.py", file=sys.stderr)
        return 1
    args.readme.write_text(updated, encoding="utf-8")
    print("README.md updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
