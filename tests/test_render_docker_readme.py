from __future__ import annotations

import subprocess
import sys

import pytest

from compose_stacks import docker as docker_mod
from compose_stacks.catalog import Catalog, Stack
from compose_stacks.render import (
    README_END,
    README_START,
    readme_table,
    replace_between_markers,
    report_github,
    report_text,
    stacks_table,
    table,
)
from compose_stacks.validate import Report
from conftest import REPO_ROOT, STACKS_DIR, write_stack


def test_table_truncates_last_column():
    out = table([["a", "x" * 200]], ["K", "V"], max_width=40)
    assert all(len(line) <= 40 for line in out.splitlines())
    assert out.splitlines()[-1].endswith("…")


def test_stacks_table_shows_broken_stack(stacks_root):
    broken = Stack.load(write_stack(stacks_root, toml="name = "))
    assert "error:" in stacks_table([broken], max_width=200)


def test_readme_table_lists_every_stack():
    stacks = list(Catalog(STACKS_DIR))
    out = readme_table(stacks)
    for stack in stacks:
        assert f"[{stack.name}](stacks/{stack.name}/)" in out
    assert out.startswith(f"**{len(stacks)} stacks**")


def test_replace_between_markers():
    text = f"before\n{README_START}\nold\n{README_END}\nafter\n"
    assert replace_between_markers(text, "new") == f"before\n{README_START}\nnew\n{README_END}\nafter\n"
    with pytest.raises(ValueError):
        replace_between_markers("no markers", "x")


def test_report_output_escapes_newlines():
    report = Report(checked=["a"])
    report.add("CS050", "a", "line1\nline2", file="compose.yaml")
    report.add("CS051", "a", "skipped")
    gh = report_github(report)
    assert "line1%0Aline2" in gh
    assert "CS051" not in gh.splitlines()[0]
    assert "FAIL  a" in report_text(report)


def test_readme_is_up_to_date():
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "gen_readme.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_gen_readme_rewrites(tmp_path, stacks_root):
    write_stack(stacks_root, "alpha")
    readme = tmp_path / "README.md"
    readme.write_text(f"# X\n{README_START}\n{README_END}\n", encoding="utf-8")
    script = str(REPO_ROOT / "scripts" / "gen_readme.py")
    args = [sys.executable, script, "--readme", str(readme), "--stacks-dir", str(stacks_root)]
    assert subprocess.run([*args, "--check"], capture_output=True, check=False).returncode == 1
    assert subprocess.run(args, capture_output=True, check=False).returncode == 0
    assert "[alpha](stacks/alpha/)" in readme.read_text()
    assert subprocess.run([*args, "--check"], capture_output=True, check=False).returncode == 0


def test_compose_config_builds_expected_command(demo_stack, monkeypatch):
    calls = {}

    class Proc:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(args, **kwargs):
        calls["args"] = args
        env_file = args[args.index("--env-file") + 1]
        with open(env_file, encoding="utf-8") as fh:
            calls["env"] = fh.read()
        return Proc()

    monkeypatch.setattr(docker_mod.subprocess, "run", fake_run)
    ok, _ = docker_mod.compose_config(Stack.load(demo_stack), ["docker", "compose"])
    assert ok
    assert calls["args"][:2] == ["docker", "compose"]
    assert calls["args"][-2:] == ["config", "--quiet"]
    assert "APP_SECRET=" in calls["env"] and "APP_SECRET=\n" not in calls["env"]


def test_docker_compose_command_detection(monkeypatch):
    monkeypatch.setattr(docker_mod.shutil, "which", lambda name: None)
    assert docker_mod.docker_compose_command() is None

    class Proc:
        returncode = 0

    monkeypatch.setattr(docker_mod.shutil, "which", lambda name: "/usr/bin/docker" if name == "docker" else None)
    monkeypatch.setattr(docker_mod.subprocess, "run", lambda *a, **k: Proc())
    assert docker_mod.docker_compose_command() == ["/usr/bin/docker", "compose"]
