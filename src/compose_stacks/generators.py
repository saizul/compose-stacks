"""Strong random value generators used by ``compose-stacks init``.

All values come from :mod:`secrets` (the operating system CSPRNG). Generated
values never contain quotes, spaces, ``#`` or ``$``, so they are safe in ``.env``
files without quoting. ``alnum``, ``hex``, ``urlsafe`` and ``uuid`` values are also
safe inside connection URLs.
"""

from __future__ import annotations

import base64
import secrets
import string
import uuid

ALNUM = string.ascii_letters + string.digits


def generate(spec: str) -> str:
    """Generate a value from a spec such as ``alnum:32``, ``hex:32``, ``base64:32`` or ``uuid``.

    ``alnum:N`` returns N characters. ``hex:N``, ``base64:N`` and ``urlsafe:N``
    encode N random bytes, matching ``openssl rand -hex N`` / ``-base64 N``.
    """

    if spec == "uuid":
        return str(uuid.uuid4())
    kind, _, size_text = spec.partition(":")
    try:
        size = int(size_text)
    except ValueError as exc:
        raise ValueError(f"invalid generator spec '{spec}'") from exc
    if not 8 <= size <= 256:
        raise ValueError(f"generator size must be between 8 and 256, got {size}")
    if kind == "alnum":
        return "".join(secrets.choice(ALNUM) for _ in range(size))
    if kind == "hex":
        return secrets.token_hex(size)
    if kind == "base64":
        return base64.b64encode(secrets.token_bytes(size)).decode("ascii")
    if kind == "urlsafe":
        return secrets.token_urlsafe(size)
    raise ValueError(f"unknown generator '{kind}'")


def openssl_hint(spec: str) -> str:
    """Return the equivalent shell command, used in docs and ``.env.example`` comments."""

    if spec == "uuid":
        return "uuidgen"
    kind, _, size = spec.partition(":")
    if kind == "hex":
        return f"openssl rand -hex {size}"
    if kind in ("base64", "urlsafe"):
        return f"openssl rand -base64 {size}"
    return f"openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | head -c {size}"
