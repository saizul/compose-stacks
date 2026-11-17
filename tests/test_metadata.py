from __future__ import annotations

import pytest

from compose_stacks.metadata import CATEGORIES, MetadataError, load_metadata, parse_metadata

VALID = {
    "name": "demo",
    "description": "A perfectly fine description",
    "category": "devtools",
    "tags": ["demo"],
    "upstream_docs": "https://example.org",
    "maintained_by": ["saizul"],
    "healthcheck": {"services": ["app"]},
}


def problems_for(**changes):
    data = {**VALID, **changes}
    data = {k: v for k, v in data.items() if v is not None}
    return parse_metadata(data)[1]


def test_valid_metadata_has_no_problems():
    meta, problems = parse_metadata(VALID)
    assert problems == []
    assert meta.name == "demo"
    assert meta.healthcheck_services == ["app"]


@pytest.mark.parametrize(
    ("changes", "fragment"),
    [
        ({"name": "Bad_Name"}, "kebab-case"),
        ({"name": None}, "'name' is required"),
        ({"description": "short"}, "10-160"),
        ({"description": "Ends with a period."}, "period"),
        ({"category": "nope"}, "'category' must be one of"),
        ({"tags": []}, "at least one tag"),
        ({"tags": ["UPPER"]}, "lowercase"),
        ({"tags": ["a", "a"]}, "duplicates"),
        ({"tags": "notalist"}, "list of strings"),
        ({"upstream_docs": "http://insecure"}, "https://"),
        ({"maintained_by": []}, "GitHub handle"),
        ({"maintained_by": ["not a handle!"]}, "not a valid GitHub handle"),
        ({"healthcheck": None}, "'[healthcheck]' table is required"),
        ({"healthcheck": {"services": []}}, "at least one service"),
        ({"healthcheck": {"services": ["a"], "exempt": {"b": "short"}}}, "reason"),
        ({"healthcheck": "x"}, "must be a table"),
        ({"surprise": 1}, "unknown key 'surprise'"),
        ({"description": 5}, "must be a string"),
    ],
)
def test_schema_problems(changes, fragment):
    problems = problems_for(**changes)
    assert any(fragment in p for p in problems), problems


def test_ports_parsing_and_problems():
    meta, problems = parse_metadata(
        {
            **VALID,
            "ports": [
                {"service": "app", "host": 8080, "container": 80},
                {"service": "app", "host": 443, "container": 443, "bind": "0.0.0.0", "protocol": "udp"},
                {"service": "", "host": 0, "container": 99999, "protocol": "sctp", "extra": 1},
                "not-a-table",
            ],
        }
    )
    assert [p.host for p in meta.ports] == [8080, 443, 0]
    assert meta.ports[0].bind == "127.0.0.1" and not meta.ports[0].public
    assert meta.ports[1].public
    joined = "\n".join(problems)
    assert "service is required" in joined
    assert "between 1 and 65535" in joined
    assert "'tcp' or 'udp'" in joined
    assert "unknown keys: extra" in joined
    assert "must be a table" in joined
    assert parse_metadata({**VALID, "ports": {}})[1]


def test_volumes_parsing():
    meta, problems = parse_metadata({**VALID, "volumes": [{"name": "data", "description": "d"}, {"x": 1}]})
    assert [v.name for v in meta.volumes] == ["data"]
    assert any("volumes[1]" in p for p in problems)
    assert parse_metadata({**VALID, "volumes": "x"})[1]


def test_env_parsing():
    meta, problems = parse_metadata(
        {
            **VALID,
            "env": {
                "GOOD": {"description": "fine", "default": 5},
                "SECRET_ONE": {"description": "s", "secret": True},
                "lower": {"description": "x"},
                "BAD_GEN": {"description": "x", "secret": True, "generate": "rot13:5"},
                "GEN_NOT_SECRET": {"description": "x", "generate": "hex:16"},
                "SECRET_DEFAULT": {"description": "x", "secret": True, "default": "abc"},
                "NO_DESC": {},
                "WEIRD": {"description": "x", "secret": "yes", "unknown": 1},
                "NOT_TABLE": "x",
            },
        }
    )
    assert meta.env["GOOD"].default == "5"
    assert meta.env["SECRET_ONE"].generate == "alnum:32"
    assert meta.env["SECRET_ONE"].required is True
    assert [v.name for v in meta.secrets] == ["SECRET_ONE", "BAD_GEN", "SECRET_DEFAULT"]
    joined = "\n".join(problems)
    for fragment in (
        "UPPER_SNAKE_CASE",
        "rot13:5",
        "only allowed together with secret",
        "must not have a default",
        "description is required",
        "secret must be true or false",
        "unknown keys: unknown",
        "env.NOT_TABLE must be a table",
    ):
        assert fragment in joined, fragment


def test_to_dict_roundtrip_keys():
    meta, _ = parse_metadata(VALID)
    data = meta.to_dict()
    assert set(data) >= {"name", "ports", "volumes", "healthcheck", "env"}


def test_load_metadata_errors(tmp_path):
    with pytest.raises(MetadataError, match="not found"):
        load_metadata(tmp_path / "stack.toml")
    bad = tmp_path / "stack.toml"
    bad.write_text("name = ", encoding="utf-8")
    with pytest.raises(MetadataError, match="not valid TOML"):
        load_metadata(bad)


def test_categories_are_described():
    assert all(desc for desc in CATEGORIES.values())
    assert list(CATEGORIES) == sorted(CATEGORIES)
