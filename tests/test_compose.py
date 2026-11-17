from __future__ import annotations

import pytest

from compose_stacks.compose import (
    ComposeError,
    environment_items,
    has_healthcheck,
    interpolate,
    is_major_only_tag,
    load_compose,
    parse_env_file,
    parse_image,
    parse_port,
    referenced_variables,
    variables_with_defaults,
)


@pytest.mark.parametrize(
    ("text", "env", "expected"),
    [
        ("${A}", {"A": "1"}, "1"),
        ("${A:-x}", {}, "x"),
        ("${A:-x}", {"A": ""}, "x"),
        ("${A-x}", {"A": ""}, ""),
        ("${A:+set}", {"A": "1"}, "set"),
        ("${A:+set}", {}, ""),
        ("${A+set}", {"A": ""}, "set"),
        ("${A:?boom}", {"A": "v"}, "v"),
        ("$$HOME", {}, "$HOME"),
        ("$A-$B", {"A": "1", "B": "2"}, "1-2"),
    ],
)
def test_interpolate(text, env, expected):
    assert interpolate(text, env) == expected


def test_referenced_variables_ignores_escaped():
    data = {"cmd": "echo $$NOT_A_VAR ${REAL} $PLAIN", "list": ["${OTHER:-1}"]}
    assert referenced_variables(data) == {"REAL", "PLAIN", "OTHER"}
    assert variables_with_defaults(data) == {"OTHER"}


@pytest.mark.parametrize(
    ("ref", "repo", "tag", "digest", "pinned"),
    [
        ("postgres:18.7-alpine", "postgres", "18.7-alpine", "", True),
        ("postgres", "postgres", "", "", False),
        ("postgres:latest", "postgres", "latest", "", False),
        ("ghcr.io/org/app:v1.2.3", "ghcr.io/org/app", "v1.2.3", "", True),
        ("localhost:5000/app", "localhost:5000/app", "", "", False),
        ("localhost:5000/app:1.0", "localhost:5000/app", "1.0", "", True),
        ("app@sha256:abc", "app", "", "sha256:abc", True),
        ("app:main", "app", "main", "", False),
    ],
)
def test_parse_image(ref, repo, tag, digest, pinned):
    image = parse_image(ref)
    assert (image.repository, image.tag, image.digest, image.pinned) == (repo, tag, digest, pinned)


@pytest.mark.parametrize(("tag", "expected"), [("18", True), ("v3", True), ("18-alpine", True), ("18.7", False)])
def test_major_only(tag, expected):
    assert is_major_only_tag(tag) is expected


@pytest.mark.parametrize(
    ("spec", "ip", "published", "target", "proto"),
    [
        ("80", "", "", "80", "tcp"),
        ("8080:80", "", "8080", "80", "tcp"),
        ("127.0.0.1:8080:80", "127.0.0.1", "8080", "80", "tcp"),
        ("0.0.0.0:443:443/udp", "0.0.0.0", "443", "443", "udp"),
        ("[::1]:53:53/udp", "::1", "53", "53", "udp"),
        ("9000-9001:9000-9001", "", "9000-9001", "9000-9001", "tcp"),
        (8080, "", "", "8080", "tcp"),
        ({"target": 80, "published": "8080", "host_ip": "127.0.0.1"}, "127.0.0.1", "8080", "80", "tcp"),
    ],
)
def test_parse_port(spec, ip, published, target, proto):
    mapping = parse_port(spec)
    assert (mapping.host_ip, mapping.published, mapping.target, mapping.protocol) == (ip, published, target, proto)


@pytest.mark.parametrize("spec", ["abc", "70000:80", "1.2.3.4:x:80", {"published": 80}, None])
def test_parse_port_invalid(spec):
    with pytest.raises(ValueError):
        parse_port(spec)


def test_parse_env_file():
    text = "# comment\nA=1\nexport B=two\nC='quoted # not a comment'\nD=value # trailing\nE=\nbad line\n"
    assert parse_env_file(text) == {"A": "1", "B": "two", "C": "quoted # not a comment", "D": "value", "E": ""}


def test_environment_items_list_and_dict():
    assert environment_items({"environment": ["A=1", "B"]}) == [("A", "1"), ("B", None)]
    assert environment_items({"environment": {"A": 1, "B": None}}) == [("A", "1"), ("B", None)]
    assert environment_items({}) == []


def test_has_healthcheck():
    assert has_healthcheck({"healthcheck": {"test": ["CMD", "true"]}})
    assert has_healthcheck({"healthcheck": {"test": "curl -f http://x"}})
    assert not has_healthcheck({"healthcheck": {"test": ["NONE"]}})
    assert not has_healthcheck({"healthcheck": {"disable": True}})
    assert not has_healthcheck({})


def test_load_compose_errors(tmp_path):
    with pytest.raises(ComposeError, match="not found"):
        load_compose(tmp_path / "missing.yaml")
    bad = tmp_path / "bad.yaml"
    bad.write_text("services: [unclosed", encoding="utf-8")
    with pytest.raises(ComposeError, match="not valid YAML"):
        load_compose(bad)
    empty = tmp_path / "empty.yaml"
    empty.write_text("volumes: {}\n", encoding="utf-8")
    with pytest.raises(ComposeError, match="at least one service"):
        load_compose(empty)
    scalar = tmp_path / "scalar.yaml"
    scalar.write_text("just text\n", encoding="utf-8")
    with pytest.raises(ComposeError, match="mapping"):
        load_compose(scalar)
