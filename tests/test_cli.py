from __future__ import annotations

import json

import pytest

from compose_stacks import __version__
from compose_stacks.cli import main
from conftest import COMPOSE, STACKS_DIR, write_stack


def run(capsys, *args):
    code = main(list(args))
    out, err = capsys.readouterr()
    return code, out, err


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_no_command_prints_help(capsys):
    code, out, _ = run(capsys)
    assert code == 2 and "usage" in out


def test_list_table(capsys):
    code, out, _ = run(capsys, "list")
    assert code == 0
    assert "wordpress" in out and "CATEGORY" in out


def test_list_json_and_filters(capsys):
    code, out, _ = run(capsys, "list", "--format", "json", "--category", "database")
    data = json.loads(out)
    assert code == 0
    assert {d["name"] for d in data} == {"postgres-pgadmin", "mysql-adminer"}
    assert all("images" in d for d in data)
    code, out, _ = run(capsys, "ls", "-t", "redis", "-f", "names")
    assert "redis" in out.split()


def test_list_unknown_category(capsys):
    code, _, err = run(capsys, "list", "-c", "nope")
    assert code == 2 and "unknown category" in err


def test_list_no_match(capsys):
    code, _, err = run(capsys, "list", "-t", "no-such-tag")
    assert code == 0 and "No stacks match" in err


def test_show(capsys):
    code, out, _ = run(capsys, "show", "n8n")
    assert code == 0
    assert "N8N_ENCRYPTION_KEY [secret" in out and "Deploy:" in out
    code, out, _ = run(capsys, "show", "n8n", "-f", "json")
    assert json.loads(out)["category"] == "automation"
    code, out, _ = run(capsys, "show", "redis", "--readme")
    assert out.startswith("# Redis")
    code, out, _ = run(capsys, "show", "redis", "--compose")
    assert "services:" in out


def test_show_unknown(capsys):
    code, _, err = run(capsys, "show", "wordpres")
    assert code == 2 and "Did you mean" in err


def test_search(capsys):
    code, out, _ = run(capsys, "search", "analytics")
    assert code == 0 and "umami" in out
    code, out, _ = run(capsys, "search", "analytics", "-f", "json")
    assert json.loads(out)[0]["name"] == "umami"
    code, _, err = run(capsys, "search", "zzzz")
    assert code == 1 and "No stacks match" in err


def test_init(capsys, tmp_path):
    target = tmp_path / "wp"
    code, out, _ = run(capsys, "init", "wordpress", str(target), "--set", "WORDPRESS_PORT=8090")
    assert code == 0
    assert "Generated strong random values for" in out
    env = (target / ".env").read_text()
    assert "WORDPRESS_PORT=8090" in env
    assert "WORDPRESS_DB_PASSWORD=\n" not in env
    code, _, err = run(capsys, "init", "wordpress", str(target))
    assert code == 2 and "--force" in err


def test_init_default_dir(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, out, _ = run(capsys, "init", "traefik")
    assert code == 0
    assert (tmp_path / "traefik" / ".env").exists()
    assert "Fill in before starting: ACME_EMAIL" in out


def test_init_bad_set(capsys, tmp_path):
    code, _, err = run(capsys, "init", "redis", str(tmp_path / "r"), "--set", "oops")
    assert code == 2 and "NAME=value" in err


def test_validate_all_passes(capsys):
    code, out, _ = run(capsys, "validate", "--all", "--strict")
    assert code == 0
    assert "0 error(s), 0 warning(s)" in out


def test_validate_by_name_and_json(capsys):
    code, out, _ = run(capsys, "validate", "redis", "mailpit", "-f", "json")
    data = json.loads(out)
    assert code == 0 and data["checked"] == ["redis", "mailpit"] and data["errors"] == 0


def test_validate_path_failure_github_format(capsys, stacks_root):
    path = write_stack(stacks_root, compose=COMPOSE.replace("example/app:1.2.3", "example/app:latest"))
    code, out, _ = run(capsys, "validate", str(path), "-f", "github")
    assert code == 1
    assert "::error file=stacks/demo/compose.yaml,title=CS013::" in out


def test_validate_strict_warning(capsys, stacks_root):
    path = write_stack(stacks_root, readme="# Demo\n")
    assert run(capsys, "validate", str(path))[0] == 0
    code, out, _ = run(capsys, "validate", str(path), "--strict", "-v")
    assert code == 1 and "CS005" in out


def test_validate_with_custom_stacks_dir(capsys, stacks_root):
    write_stack(stacks_root, "alpha")
    code, out, _ = run(capsys, "--stacks-dir", str(stacks_root), "validate")
    assert code == 0 and "alpha" in out


def test_validate_docker_skipped_without_docker(capsys, monkeypatch):
    monkeypatch.setattr("compose_stacks.docker.docker_compose_command", lambda: None)
    code, out, _ = run(capsys, "validate", "redis", "--docker", "-v")
    assert code == 0 and "CS051" in out
    code, _, err = run(capsys, "validate", "redis", "--require-docker")
    assert code == 2 and "required" in err


def test_validate_docker_failure_reported(capsys, monkeypatch):
    monkeypatch.setattr("compose_stacks.docker.docker_compose_command", lambda: ["docker", "compose"])
    monkeypatch.setattr("compose_stacks.docker.compose_config", lambda stack, cmd: (False, "boom"))
    code, out, _ = run(capsys, "validate", "redis", "--docker")
    assert code == 1 and "CS050" in out and "boom" in out


def test_new(capsys, stacks_root):
    code, out, _ = run(capsys, "--stacks-dir", str(stacks_root), "new", "my-tool", "-c", "search", "-m", "octocat")
    assert code == 0 and "Created" in out
    assert (stacks_root / "my-tool" / "stack.toml").exists()
    code, _, err = run(capsys, "--stacks-dir", str(stacks_root), "new", "my-tool")
    assert code == 2 and "already exists" in err


def test_categories_and_rules(capsys):
    code, out, _ = run(capsys, "categories")
    assert code == 0 and "monitoring" in out
    assert "proxy" in json.loads(run(capsys, "categories", "-f", "json")[1])
    code, out, _ = run(capsys, "rules")
    assert "CS013" in out
    assert "| CS015 | error |" in run(capsys, "rules", "-f", "markdown")[1]
    assert json.loads(run(capsys, "rules", "-f", "json")[1])["CS001"]["level"] == "error"


def test_stacks_dir_missing(capsys, tmp_path):
    code, _, err = run(capsys, "--stacks-dir", str(tmp_path / "nope"), "list")
    assert code == 2 and "not found" in err


def test_module_entry_point_matches():
    assert STACKS_DIR.is_dir()
