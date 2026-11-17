from __future__ import annotations

import base64
import re
import uuid

import pytest

from compose_stacks.generators import generate, openssl_hint


def test_alnum_length_and_charset():
    value = generate("alnum:40")
    assert len(value) == 40
    assert re.fullmatch(r"[A-Za-z0-9]+", value)


def test_hex_is_bytes_times_two():
    assert re.fullmatch(r"[0-9a-f]{64}", generate("hex:32"))


def test_base64_decodes_to_requested_bytes():
    assert len(base64.b64decode(generate("base64:24"))) == 24


def test_urlsafe_and_uuid():
    assert re.fullmatch(r"[A-Za-z0-9_-]+", generate("urlsafe:32"))
    uuid.UUID(generate("uuid"))


def test_values_are_unique():
    assert len({generate("hex:16") for _ in range(50)}) == 50


@pytest.mark.parametrize("spec", ["alnum:4", "hex:999", "rot13:16", "alnum:x", "alnum"])
def test_invalid_specs(spec):
    with pytest.raises(ValueError):
        generate(spec)


def test_openssl_hints():
    assert openssl_hint("hex:32") == "openssl rand -hex 32"
    assert openssl_hint("base64:24") == "openssl rand -base64 24"
    assert "head -c 20" in openssl_hint("alnum:20")
    assert openssl_hint("uuid") == "uuidgen"
