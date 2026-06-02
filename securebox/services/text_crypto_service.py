"""Text encryption service."""

from __future__ import annotations

import json
import os
from typing import Any

from securebox.config import APP_NAME, CRYPTO_VERSION
from securebox.crypto.aead import blob_from_json, blob_to_json, decrypt_text, encrypt_text
from securebox.crypto.kdf import KdfConfig, default_argon2id_config, derive_key
from securebox.utils.encoding import b64decode, b64encode

TEXT_PACKAGE_TYPE = "securebox-text"


def encrypt_text_with_key(data_key: bytes, plaintext: str) -> str:
    blob = encrypt_text(data_key, plaintext, _text_aad("session"))
    return blob_to_json(blob)


def decrypt_text_with_key(data_key: bytes, payload: str) -> str:
    return decrypt_text(data_key, blob_from_json(payload), _text_aad("session"))


def encrypt_text_with_password(
    password: str,
    plaintext: str,
    kdf_config: KdfConfig | None = None,
) -> str:
    config = kdf_config or default_argon2id_config(os.urandom(16))
    key = derive_key(password, config)
    blob = encrypt_text(key, plaintext, _text_aad("password"))
    package: dict[str, Any] = {
        "type": TEXT_PACKAGE_TYPE,
        "crypto_version": CRYPTO_VERSION,
        "kdf": config.to_dict(),
        "blob": blob.to_dict(),
    }
    return b64encode(json.dumps(package, separators=(",", ":")).encode())


def decrypt_text_with_password(password: str, payload: str) -> str:
    package = json.loads(b64decode(payload).decode())
    if package.get("type") != TEXT_PACKAGE_TYPE:
        raise ValueError("Unsupported text encryption package")
    config = KdfConfig.from_dict(package["kdf"])
    key = derive_key(password, config)
    return decrypt_text(key, blob_from_json(json.dumps(package["blob"])), _text_aad("password"))


def _text_aad(mode: str) -> bytes:
    return f"{APP_NAME}:text:{mode}:v{CRYPTO_VERSION}".encode()

