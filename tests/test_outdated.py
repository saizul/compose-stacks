from __future__ import annotations

import json
from pathlib import Path

import pytest

from compose_stacks.catalog import Catalog, Stack
from compose_stacks.cli import main
from compose_stacks.outdated import check_directory, compare_deployment, detect_stack_name, render_text
from compose_stacks.scaffold import ScaffoldError, init_stack
from conftest import COMPOSE, ENV_EXAMPLE, STACKS_DIR, write_stack


def deploy(stacks_root: Path, tmp_path: Path, name: str = "demo") -> Path:
    target = tmp_path / "deployed" / name
    init_stack(Stack.load(stacks_root / name), target)
    return target


def test_fresh_deployment_is_up_to_date(demo_stack, stacks_root, tmp_path):
    target = deploy(stacks_root, tmp_path)
    report = compare_deployment(target, Stack.load(demo_stack))
    assert not report.outdated
    assert report.up_to_date == ["app"] and report.images == [] and report.missing_env == []
    assert "up to date" in render_text([report])


def test_library_bump_and_new_variable(demo_stack, stacks_root, tmp_path):
    target = deploy(stacks_root, tmp_path)
    (demo_stack / "compose.yaml").write_text(
        COMPOSE.replace("example/app:1.2.3", "example/app:1.3.0"),
        encoding="utf-8",
    )
    (demo_stack / ".env.example").write_text(ENV_EXAMPLE + "APP_WORKERS=4\n", encoding="utf-8")
    report = compare_deployment(target, Stack.load(demo_stack))
    assert report.outdated
    assert [(c.service, c.kind, c.deployed, c.library) for c in report.images] == [
        ("app", "changed", "example/app:1.2.3", "example/app:1.3.0")
    ]
    assert report.missing_env == ["APP_WORKERS"]
    text = render_text([report])
    assert "app: example/app:1.2.3 -> example/app:1.3.0" in text
    assert ".env is missing: APP_WORKERS" in text
    assert "docker compose pull" in text


def test_added_and_extra_services(demo_stack, stacks_root, tmp_path):
    target = deploy(stacks_root, tmp_path)
    extra = "  cron:\n    image: example/cron:2\n"
    deployed = (target / "compose.yaml").read_text(encoding="utf-8").replace("\nvolumes:", extra + "\nvolumes:", 1)
    (target / "compose.yaml").write_text(deployed, encoding="utf-8")
    sidecar = "  worker:\n    image: example/worker:0.9.0\n"
    (demo_stack / "compose.yaml").write_text(COMPOSE.replace("\nvolumes:", sidecar + "\nvolumes:", 1), encoding="utf-8")
    report = compare_deployment(target, Stack.load(demo_stack))
    kinds = {c.service: c.kind for c in report.images}
    assert kinds == {"cron": "extra", "worker": "added"}
    assert report.outdated  # the added service counts, the extra one does not
    assert "cron: not in the library (example/cron:2), left alone" in render_text([report])


def test_only_extra_services_is_not_outdated(demo_stack, stacks_root, tmp_path):
    target = deploy(stacks_root, tmp_path)
    deployed = (target / "compose.yaml").read_text(encoding="utf-8")
    deployed = deployed.replace("\nvolumes:", "  cron:\n    image: example/cron:2\n\nvolumes:", 1)
    (target / "compose.yaml").write_text(deployed, encoding="utf-8")
    assert not compare_deployment(target, Stack.load(demo_stack)).outdated


def test_image_tags_from_env_are_interpolated(stacks_root, tmp_path):
    compose = COMPOSE.replace("example/app:1.2.3", "example/app:${APP_VERSION:-1.2.3}")
    stack_dir = write_stack(stacks_root, compose=compose, env=ENV_EXAMPLE + "APP_VERSION=1.4.0\n")
    target = deploy(stacks_root, tmp_path)
    assert not compare_deployment(target, Stack.load(stack_dir)).outdated
    # An older version pinned in the folder's .env is reported against the library default.
    env = (target / ".env").read_text(encoding="utf-8").replace("APP_VERSION=1.4.0", "APP_VERSION=1.1.0")
    (target / ".env").write_text(env, encoding="utf-8")
    report = compare_deployment(target, Stack.load(stack_dir))
    assert [(c.deployed, c.library) for c in report.images] == [("example/app:1.1.0", "example/app:1.4.0")]


def test_detect_stack_name(tmp_path):
    folder = tmp_path / "my-blog"
    folder.mkdir()
    assert detect_stack_name(folder) == "my-blog"
    (folder / "stack.toml").write_text('name = "wordpress"\n', encoding="utf-8")
    assert detect_stack_name(folder) == "wordpress"
    (folder / "stack.toml").write_text("name = [broken\n", encoding="utf-8")
    with pytest.raises(ScaffoldError, match="--stack"):
        detect_stack_name(folder)


def test_errors(demo_stack, stacks_root, tmp_path):
    catalog = Catalog(stacks_root)
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ScaffoldError, match="pass --stack"):
        check_directory(empty, catalog)
    with pytest.raises(ScaffoldError, match=r"no compose\.yaml"):
        check_directory(empty, catalog, "demo")


def test_cli_exit_codes_and_json(capsys, demo_stack, stacks_root, tmp_path):
    target = deploy(stacks_root, tmp_path)
    assert main(["--stacks-dir", str(stacks_root), "outdated", str(target)]) == 0
    capsys.readouterr()
    (demo_stack / "compose.yaml").write_text(COMPOSE.replace("1.2.3", "2.0.0"), encoding="utf-8")
    assert main(["--stacks-dir", str(stacks_root), "outdated", str(target), "-f", "json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data[0]["stack"] == "demo" and data[0]["outdated"] is True
    assert data[0]["images"][0] == {
        "service": "app",
        "change": "changed",
        "deployed": "example/app:1.2.3",
        "library": "example/app:2.0.0",
    }
    renamed = tmp_path / "elsewhere"
    target.rename(renamed)
    (renamed / "stack.toml").unlink()
    assert main(["--stacks-dir", str(stacks_root), "outdated", str(renamed)]) == 2
    assert main(["--stacks-dir", str(stacks_root), "outdated", str(renamed), "--stack", "demo"]) == 1


def test_every_bundled_stack_is_up_to_date_after_init(tmp_path):
    catalog = Catalog(STACKS_DIR)
    for stack in catalog:
        target = tmp_path / stack.name
        init_stack(stack, target)
        report = check_directory(target, catalog)
        assert not report.outdated, (stack.name, report.to_dict())
