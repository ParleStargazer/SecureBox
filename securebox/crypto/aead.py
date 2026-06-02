"""Authenticated encryption helpers."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from securebox.config import CRYPTO_VERSION
from securebox.utils.encoding import b64decode, b64encode
from securebox.utils.errors import (
    AuthenticationFailedError,
    UnsupportedCryptoVersionError,
)

AES_GCM_ALGORITHM = "AES-256-GCM"
KEY_SIZE = 32
NONCE_SIZE = 12
TAG_SIZE = 16


@dataclass(frozen=True)
class EncryptedBlob:
    algorithm: str
    nonce: bytes
    ciphertext: bytes
    tag: bytes
    crypto_version: int = CRYPTO_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "nonce": b64encode(self.nonce),
            "ciphertext": b64encode(self.ciphertext),
            "tag": b64encode(self.tag),
            "crypto_version": self.crypto_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> EncryptedBlob:
        return cls(
            algorithm=payload["algorithm"],
            nonce=b64decode(payload["nonce"]),
            ciphertext=b64decode(payload["ciphertext"]),
            tag=b64decode(payload["tag"]),
            crypto_version=int(payload.get("crypto_version", CRYPTO_VERSION)),
        )


def encrypt_bytes(key: bytes, plaintext: bytes, aad: bytes = b"") -> EncryptedBlob:
    _validate_key(key)
    nonce = os.urandom(NONCE_SIZE)
    encrypted = AESGCM(key).encrypt(nonce, plaintext, aad)
    return EncryptedBlob(
        algorithm=AES_GCM_ALGORITHM,
        nonce=nonce,
        ciphertext=encrypted[:-TAG_SIZE],
        tag=encrypted[-TAG_SIZE:],
    )


def decrypt_bytes(key: bytes, blob: EncryptedBlob, aad: bytes = b"") -> bytes:
    _validate_key(key)
    _validate_blob(blob)
    try:
        return AESGCM(key).decrypt(blob.nonce, blob.ciphertext + blob.tag, aad)
    except InvalidTag as exc:
        raise AuthenticationFailedError("Decryption failed authentication") from exc


def encrypt_text(key: bytes, plaintext: str, aad: bytes = b"") -> EncryptedBlob:
    return encrypt_bytes(key, plaintext.encode("utf-8"), aad)


def decrypt_text(key: bytes, blob: EncryptedBlob, aad: bytes = b"") -> str:
    return decrypt_bytes(key, blob, aad).decode("utf-8")


def blob_to_json(blob: EncryptedBlob) -> str:
    return json.dumps(blob.to_dict(), separators=(",", ":"))


def blob_from_json(payload: str) -> EncryptedBlob:
    return EncryptedBlob.from_dict(json.loads(payload))


def _validate_key(key: bytes) -> None:
    if len(key) != KEY_SIZE:
        raise ValueError("AES-256-GCM requires a 32-byte key")


def _validate_blob(blob: EncryptedBlob) -> None:
    if blob.algorithm != AES_GCM_ALGORITHM:
        raise ValueError(f"Unsupported algorithm: {blob.algorithm}")
    if blob.crypto_version != CRYPTO_VERSION:
        raise UnsupportedCryptoVersionError(
            f"Unsupported crypto version: {blob.crypto_version}"
        )
    if len(blob.nonce) != NONCE_SIZE:
        raise ValueError("AES-GCM nonce must be 12 bytes")
    if len(blob.tag) != TAG_SIZE:
        raise ValueError("AES-GCM tag must be 16 bytes")
