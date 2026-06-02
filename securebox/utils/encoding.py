"""Encoding helpers for binary data stored as text."""

from __future__ import annotations

import base64


def b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


def b64decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data.encode("ascii"))

