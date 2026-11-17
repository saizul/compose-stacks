from __future__ import annotations

import os
import stat

import pytest

from compose_stacks.catalog import Stack
from compose_stacks.compose import parse_env_file
from compose_stacks.scaffold import ScaffoldError, init_stack, new_stack, parse_overrides, render_env
from compose_stacks.validate import validate_stack
from conftest import STACK_TOML, write_stack


def test_init_copies_and_generates(demo_stack, tmp_path):
    target = tmp_path / "deploy"
    result = init_stack(Stack.load(demo_stack), target)
    assert (target / "compose.yaml").is_file()
    assert (target / "README.md").is_file()
    env = parse_env_file((target / ".env").read_text())
    assert len(env["APP_SECRET"]) == 32  # hex:16
    assert env["APP_PORT"] == "8080"
    assert result.generated == ["APP_SECRET"]
    assert result.missing_required == []
    if os.name == "posix":
        assert stat.S_IMODE((target / ".env").stat().st_mode) == 0o600


def test_init_preserves_comments(demo_stack, tmp_path):
    init_stack(Stack.load(demo_stack), tmp_path / "d")
    text = (tmp_path / "d" / ".env").read_text()
    assert "# Generate: openssl rand -hex 32" in text


def test_init_refuses_to_overwrite(demo_stack, tmp_path):
    target = tmp_path / "deploy"
    init_stack(Stack.load(demo_stack), target)
    first = (target / ".env").read_text()
    with pytest.raises(ScaffoldError, match="--force"):
        init_stack(Stack.load(demo_stack), target)
    init_stack(Stack.load(demo_stack), target, force=True)
    assert (target / ".env").read_text() != first


def test_init_into_existing_empty_dir(demo_stack, tmp_path):
    target = tmp_path / "empty"
    target.mkdir()
    init_stack(Stack.load(demo_stack), target)
    assert (target / ".env").exists()


def test_init_target_is_file(demo_stack, tmp_path):
    target = tmp_path / "file"
    target.write_text("x")
    with pytest.raises(ScaffoldError, match="not a directory"):
        init_stack(Stack.load(demo_stack), target)


def test_init_refuses_source_folder(demo_stack):
    with pytest.raises(ScaffoldError, match="own source"):
        init_stack(Stack.load(demo_stack), demo_stack, force=True)


def test_init_does_not_copy_local_env(demo_stack, tmp_path):
    (demo_stack / ".env").write_text("APP_SECRET=leaked\n")
    init_stack(Stack.load(demo_stack), tmp_path / "d")
    assert "leaked" not in (tmp_path / "d" / ".env").read_text()


def test_overrides_and_no_secrets(demo_stack):
    stack = Stack.load(demo_stack)
    text = render_env(stack, {"APP_PORT": "9000", "NEW_VAR": "x"}, generate_secrets=False)
    env = parse_env_file(text)
    assert env["APP_PORT"] == "9000"
    assert env["NEW_VAR"] == "x"
    assert env["APP_SECRET"] == ""


def test_missing_required_reported(stacks_root, tmp_path):
    toml = STACK_TOML + '\n[env.ADMIN_EMAIL]\ndescription = "Required e-mail"\nrequired = true\n'
    from conftest import ENV_EXAMPLE

    path = write_stack(stacks_root, toml=toml, env=ENV_EXAMPLE + "ADMIN_EMAIL=\n")
    result = init_stack(Stack.load(path), tmp_path / "d")
    assert result.missing_required == ["ADMIN_EMAIL"]


def test_secret_missing_from_example_is_appended(stacks_root):
    toml = STACK_TOML + '\n[env.EXTRA_KEY]\ndescription = "x"\nsecret = true\n'
    path = write_stack(stacks_root, toml=toml)
    env = parse_env_file(render_env(Stack.load(path)))
    assert len(env["EXTRA_KEY"]) == 32


def test_parse_overrides():
    assert parse_overrides(["A=1", "B=x=y", "C="]) == {"A": "1", "B": "x=y", "C": ""}
    with pytest.raises(ScaffoldError):
        parse_overrides(["novalue"])
    with pytest.raises(ScaffoldError):
        parse_overrides(["1BAD=x"])


def test_new_stack_from_template_validates(stacks_root):
    dest = new_stack("my-app", stacks_root, category="monitoring", maintainer="octocat")
    text = (dest / "stack.toml").read_text()
    assert 'name = "my-app"' in text and 'category = "monitoring"' in text and "octocat" in text
    report = validate_stack(Stack.load(dest))
    assert report.ok(strict=True), [i.message for i in report.issues]


def test_new_stack_errors(stacks_root):
    with pytest.raises(ScaffoldError, match="kebab-case"):
        new_stack("Bad Name", stacks_root)
    with pytest.raises(ScaffoldError, match="unknown category"):
        new_stack("ok", stacks_root, category="nope")
    new_stack("dup", stacks_root)
    with pytest.raises(ScaffoldError, match="already exists"):
        new_stack("dup", stacks_root)
