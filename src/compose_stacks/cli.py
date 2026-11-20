"""Command line interface: ``compose-stacks list|show|search|init|validate|new|categories``."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from compose_stacks import render
from compose_stacks._version import __version__
from compose_stacks.catalog import Catalog, CatalogError, Stack
from compose_stacks.metadata import CATEGORIES
from compose_stacks.scaffold import ScaffoldError, init_stack, new_stack, parse_overrides
from compose_stacks.validate import RULES, Report, validate_stack

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_USAGE = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compose-stacks",
        description="Production-ready Docker Compose stacks: list, search, validate and deploy them in one minute.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--stacks-dir",
        metavar="DIR",
        help="use stacks from DIR (default: $COMPOSE_STACKS_DIR, the repository checkout or the bundled library)",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    p = sub.add_parser("list", aliases=["ls"], help="list stacks")
    p.add_argument("-c", "--category", help="only stacks in this category")
    p.add_argument("-t", "--tag", action="append", default=[], help="only stacks with this tag (repeatable)")
    p.add_argument("-f", "--format", choices=["table", "json", "names"], default="table")

    p = sub.add_parser("show", help="show details of a stack")
    p.add_argument("name")
    p.add_argument("-f", "--format", choices=["text", "json"], default="text")
    p.add_argument("--readme", action="store_true", help="print the stack README")
    p.add_argument("--compose", action="store_true", help="print compose.yaml")

    p = sub.add_parser("search", help="search names, tags, categories, descriptions and images")
    p.add_argument("term", nargs="+")
    p.add_argument("-f", "--format", choices=["table", "json"], default="table")

    p = sub.add_parser("init", help="copy a stack into a folder and write a .env with strong random secrets")
    p.add_argument("name")
    p.add_argument("dir", nargs="?", help="target folder (default: ./<name>)")
    p.add_argument("--set", action="append", default=[], metavar="NAME=VALUE", help="set a variable (repeatable)")
    p.add_argument("--force", action="store_true", help="overwrite compose.yaml and .env in the target folder")
    p.add_argument("--no-secrets", action="store_true", help="leave secret variables empty")

    p = sub.add_parser("outdated", help="compare deployed stack folders with the library (image tags, new variables)")
    p.add_argument("dirs", nargs="+", metavar="DIR", help="folders created with 'compose-stacks init'")
    p.add_argument("-s", "--stack", help="library stack name (default: name in DIR/stack.toml, else the folder name)")
    p.add_argument("-f", "--format", choices=["text", "json"], default="text")

    p = sub.add_parser("validate", help="check stacks against the library rules")
    p.add_argument("targets", nargs="*", metavar="NAME_OR_PATH", help="stack names or stack folders")
    p.add_argument("--all", action="store_true", help="validate every stack")
    p.add_argument("-f", "--format", choices=["text", "json", "github"], default="text")
    p.add_argument("--strict", action="store_true", help="treat warnings as errors")
    p.add_argument("--docker", action="store_true", help="also run 'docker compose config' when docker is available")
    p.add_argument("--require-docker", action="store_true", help="like --docker, but fail when docker is missing")
    p.add_argument("-v", "--verbose", action="store_true", help="show hints and info messages")

    p = sub.add_parser("new", help="start a new stack from the template (for contributors)")
    p.add_argument("name")
    p.add_argument("-c", "--category", default="devtools", choices=sorted(CATEGORIES))
    p.add_argument("-m", "--maintainer", default="your-github-handle", help="your GitHub handle")

    p = sub.add_parser("categories", help="list allowed categories")
    p.add_argument("-f", "--format", choices=["table", "json"], default="table")

    p = sub.add_parser("rules", help="list validation rules")
    p.add_argument("-f", "--format", choices=["table", "json", "markdown"], default="table")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return EXIT_USAGE
    try:
        return _dispatch(args)
    except (CatalogError, ScaffoldError) as exc:
        print(f"compose-stacks: error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except BrokenPipeError:  # pragma: no cover - e.g. `compose-stacks list | head`
        return EXIT_OK


def _dispatch(args: argparse.Namespace) -> int:
    command = {"ls": "list"}.get(args.command, args.command)
    if command == "categories":
        return cmd_categories(args)
    if command == "rules":
        return cmd_rules(args)
    if command == "validate":
        return cmd_validate(args)
    catalog = Catalog.discover(args.stacks_dir)
    if command == "new":
        dest = new_stack(args.name, catalog.root, category=args.category, maintainer=args.maintainer)
        print(f"Created {dest}")
        print("Next: edit compose.yaml, .env.example, stack.toml and README.md, then run")
        print(f"  compose-stacks validate {args.name} --docker")
        return EXIT_OK
    commands = {"list": cmd_list, "show": cmd_show, "search": cmd_search, "init": cmd_init, "outdated": cmd_outdated}
    return commands[command](args, catalog)


def cmd_list(args: argparse.Namespace, catalog: Catalog) -> int:
    if args.category and args.category not in CATEGORIES:
        print(f"compose-stacks: unknown category '{args.category}'. Try: compose-stacks categories", file=sys.stderr)
        return EXIT_USAGE
    stacks = catalog.filter(args.category, args.tag)
    if args.format == "json":
        print(render.stacks_json(stacks))
    elif args.format == "names":
        for s in stacks:
            print(s.name)
    elif stacks:
        print(render.stacks_table(stacks))
    else:
        print("No stacks match.", file=sys.stderr)
    return EXIT_OK


def cmd_show(args: argparse.Namespace, catalog: Catalog) -> int:
    stack = catalog.get(args.name)
    if args.readme:
        print(stack.readme())
    elif args.compose:
        print((stack.path / "compose.yaml").read_text(encoding="utf-8"))
    elif args.format == "json":
        print(json.dumps(stack.summary(), indent=2))
    else:
        print(render.show_stack(stack))
    return EXIT_OK


def cmd_search(args: argparse.Namespace, catalog: Catalog) -> int:
    results = catalog.search(" ".join(args.term))
    stacks = [s for _, s in results]
    if args.format == "json":
        print(render.stacks_json(stacks))
        return EXIT_OK
    if not stacks:
        print(f"No stacks match '{' '.join(args.term)}'.", file=sys.stderr)
        return EXIT_INVALID
    print(render.stacks_table(stacks))
    return EXIT_OK


def cmd_init(args: argparse.Namespace, catalog: Catalog) -> int:
    stack = catalog.get(args.name)
    target = Path(args.dir) if args.dir else Path.cwd() / stack.name
    overrides = parse_overrides(args.set)
    result = init_stack(stack, target, overrides=overrides, force=args.force, generate_secrets=not args.no_secrets)
    print(f"Initialised {stack.name} in {result.target}")
    if result.generated:
        print(f"  Generated strong random values for: {', '.join(result.generated)}")
    if result.overridden:
        print(f"  Set from --set: {', '.join(result.overridden)}")
    print("  .env written with mode 600. Keep it out of version control.")
    if result.missing_required:
        print(f"  Fill in before starting: {', '.join(result.missing_required)}")
    if stack.metadata and stack.metadata.notes:
        print(f"  Note: {stack.metadata.notes}")
    print()
    print("Next steps:")
    print(f"  cd {result.target}")
    print("  docker compose up -d")
    print("  docker compose ps   # wait until every service reports (healthy)")
    return EXIT_OK


def cmd_outdated(args: argparse.Namespace, catalog: Catalog) -> int:
    from compose_stacks.outdated import check_directory, render_json, render_text

    reports = [check_directory(Path(d), catalog, args.stack) for d in args.dirs]
    print(render_json(reports) if args.format == "json" else render_text(reports))
    return EXIT_INVALID if any(r.outdated for r in reports) else EXIT_OK


def _resolve_targets(args: argparse.Namespace) -> list[Stack]:
    if args.all or not args.targets:
        catalog = Catalog.discover(args.stacks_dir)
        return list(catalog)
    stacks: list[Stack] = []
    catalog: Catalog | None = None
    for target in args.targets:
        path = Path(target)
        if (path.is_dir() and (path / "stack.toml").exists()) or (path.is_dir() and (path / "compose.yaml").exists()):
            stacks.append(Stack.load(path.resolve()))
            continue
        if catalog is None:
            catalog = Catalog.discover(args.stacks_dir)
        stacks.append(catalog.get(target))
    return stacks


def cmd_validate(args: argparse.Namespace) -> int:
    stacks = _resolve_targets(args)
    report = Report()
    command = None
    use_docker = args.docker or args.require_docker
    if use_docker:
        from compose_stacks.docker import docker_compose_command

        command = docker_compose_command()
        if command is None and args.require_docker:
            print("compose-stacks: error: docker compose is required but was not found", file=sys.stderr)
            return EXIT_USAGE
    for stack in stacks:
        stack_report = validate_stack(stack)
        if use_docker and not stack_report.errors:
            from compose_stacks.docker import docker_check

            docker_check(stack, stack_report, command)
        report.extend(stack_report)

    if args.format == "json":
        print(render.report_json(report))
    elif args.format == "github":
        print(render.report_github(report))
    else:
        print(render.report_text(report, verbose=args.verbose))
    return EXIT_OK if report.ok(strict=args.strict) else EXIT_INVALID


def cmd_categories(args: argparse.Namespace) -> int:
    if args.format == "json":
        print(json.dumps(CATEGORIES, indent=2))
    else:
        print(render.table([[k, v] for k, v in CATEGORIES.items()], ["CATEGORY", "DESCRIPTION"]))
    return EXIT_OK


def cmd_rules(args: argparse.Namespace) -> int:
    if args.format == "json":
        print(json.dumps({k: {"level": v[0], "description": v[1]} for k, v in RULES.items()}, indent=2))
    elif args.format == "markdown":
        print("| Code | Level | Rule |")
        print("| --- | --- | --- |")
        for code, (level, text) in RULES.items():
            print(f"| {code} | {level} | {text} |")
    else:
        print(render.table([[k, v[0], v[1]] for k, v in RULES.items()], ["CODE", "LEVEL", "RULE"]))
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
