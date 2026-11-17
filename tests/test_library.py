"""The real stack library must always pass its own rules."""

from __future__ import annotations

import pytest

from compose_stacks.catalog import Catalog
from compose_stacks.compose import parse_image
from compose_stacks.validate import validate_stack
from conftest import STACKS_DIR

CATALOG = Catalog(STACKS_DIR)
NAMES = sorted(CATALOG.stacks)


def test_library_has_at_least_fifteen_stacks():
    assert len(NAMES) >= 15


@pytest.mark.parametrize("name", NAMES)
def test_stack_passes_strict_validation(name):
    report = validate_stack(CATALOG.get(name))
    assert report.ok(strict=True), [f"{i.code} {i.message}" for i in report.issues]


@pytest.mark.parametrize("name", NAMES)
def test_images_are_pinned(name):
    for image in CATALOG.get(name).images():
        ref = parse_image(image)
        assert ref.pinned and ref.tag != "latest", image


@pytest.mark.parametrize("name", NAMES)
def test_env_example_never_contains_secret_values(name):
    stack = CATALOG.get(name)
    defaults = stack.env_defaults
    for var in stack.metadata.secrets:
        assert defaults.get(var.name, "") == "", var.name


def test_categories_used_are_diverse():
    categories = {s.metadata.category for s in CATALOG}
    assert len(categories) >= 10
