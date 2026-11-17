"""Print every stack with its images and published ports as JSON.

Run from a clone of the repository or with compose-stacks installed:

    python examples/list-as-json.py
"""

from __future__ import annotations

import json

from compose_stacks import Catalog, validate_stack


def main() -> None:
    catalog = Catalog.discover()
    rows = []
    for stack in catalog:
        meta = stack.metadata
        if meta is None:
            continue
        report = validate_stack(stack)
        rows.append(
            {
                "name": stack.name,
                "category": meta.category,
                "images": stack.images(),
                "ports": [f"{p.bind}:{p.host}->{p.container}/{p.protocol}" for p in meta.ports],
                "secrets": [v.name for v in meta.secrets],
                "valid": report.ok(),
            }
        )
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
