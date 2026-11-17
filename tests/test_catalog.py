from __future__ import annotations

import pytest

from compose_stacks.catalog import Catalog, CatalogError, Stack, find_stacks_dir
from conftest import STACK_TOML, STACKS_DIR, write_stack


def test_find_stacks_dir_explicit_and_env(tmp_path, monkeypatch):
    assert find_stacks_dir(tmp_path) == tmp_path.resolve()
    monkeypatch.setenv("COMPOSE_STACKS_DIR", str(tmp_path))
    assert find_stacks_dir() == tmp_path.resolve()
    with pytest.raises(CatalogError):
        find_stacks_dir(tmp_path / "missing")


def test_find_stacks_dir_defaults_to_repo(monkeypatch):
    monkeypatch.delenv("COMPOSE_STACKS_DIR", raising=False)
    assert find_stacks_dir() == STACKS_DIR.resolve()


def test_catalog_skips_hidden_and_non_stacks(stacks_root):
    write_stack(stacks_root, "alpha")
    write_stack(stacks_root, "_draft")
    (stacks_root / "notes").mkdir()
    (stacks_root / "file.txt").write_text("x")
    catalog = Catalog(stacks_root)
    assert list(catalog.stacks) == ["alpha"]
    assert len(catalog) == 1


def test_get_suggests_close_names(stacks_root):
    write_stack(stacks_root, "wordpress")
    with pytest.raises(CatalogError, match="Did you mean: wordpress"):
        Catalog(stacks_root).get("wordpres")


def test_filter_by_category_and_tags(stacks_root):
    write_stack(stacks_root, "alpha")
    write_stack(
        stacks_root,
        "beta",
        toml=STACK_TOML.replace('name = "demo"', 'name = "beta"')
        .replace('category = "devtools"', 'category = "database"')
        .replace('tags = ["demo", "test"]', 'tags = ["sql"]'),
    )
    catalog = Catalog(stacks_root)
    assert [s.name for s in catalog.filter(category="database")] == ["beta"]
    assert [s.name for s in catalog.filter(tags=["demo", "test"])] == ["alpha"]
    assert [s.name for s in catalog.filter(tags=["demo", "sql"])] == []


def test_search_ranking():
    catalog = Catalog(STACKS_DIR)
    names = [s.name for _, s in catalog.search("redis")]
    assert names[0] == "redis"
    assert "wordpress" in names and "nextcloud" in names
    assert next(s.name for _, s in catalog.search("postgres pgadmin")) == "postgres-pgadmin"
    assert catalog.search("definitely-not-here") == []
    assert catalog.search("   ") == []


def test_search_matches_images():
    names = [s.name for _, s in Catalog(STACKS_DIR).search("getmeili")]
    assert names == ["meilisearch"]


def test_stack_summary_and_errors(stacks_root):
    path = write_stack(stacks_root, toml="name = ")
    stack = Stack.load(path)
    assert not stack.ok
    assert "error" in stack.summary()
    good = Stack.load(write_stack(stacks_root, "good"))
    summary = good.summary()
    assert summary["services"] == ["app"]
    assert summary["images"] == ["example/app:1.2.3"]


def test_compose_error_property(stacks_root):
    stack = Stack.load(write_stack(stacks_root, compose="services: ["))
    assert "not valid YAML" in stack.compose_error
    assert stack.services == []
    assert stack.images() == []
