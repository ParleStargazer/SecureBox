import os

import pytest

from securebox.crypto.aead import (
    EncryptedBlob,
    decrypt_bytes,
    decrypt_text,
    encrypt_bytes,
    encrypt_text,
)
from securebox.utils.errors import AuthenticationFailedError


def test_encrypt_decrypt_roundtrip() -> None:
    key = os.urandom(32)
    aad = b"entry:1:password:v1"

    blob = encrypt_bytes(key, b"secret password", aad)

    assert blob.ciphertext != b"secret password"
    assert decrypt_bytes(key, blob, aad) == b"secret password"


def test_encrypt_uses_unique_nonce() -> None:
    key = os.urandom(32)

    first = encrypt_bytes(key, b"same")
    second = encrypt_bytes(key, b"same")

    assert first.nonce != second.nonce
    assert first.ciphertext != second.ciphertext


def test_tampered_ciphertext_fails_authentication() -> None:
    key = os.urandom(32)
    blob = encrypt_bytes(key, b"secret")
    tampered = EncryptedBlob(
        algorithm=blob.algorithm,
        nonce=blob.nonce,
        ciphertext=blob.ciphertext[:-1] + bytes([blob.ciphertext[-1] ^ 1]),
        tag=blob.tag,
        crypto_version=blob.crypto_version,
    )

    with pytest.raises(AuthenticationFailedError):
        decrypt_bytes(key, tampered)


def test_wrong_aad_fails_authentication() -> None:
    key = os.urandom(32)
    blob = encrypt_text(key, "alice-password", b"entry:1:password:v1")

    with pytest.raises(AuthenticationFailedError):
        decrypt_text(key, blob, b"entry:1:username:v1")


def test_blob_serialization_roundtrip() -> None:
    key = os.urandom(32)
    blob = encrypt_text(key, "hello", b"field")

    restored = EncryptedBlob.from_dict(blob.to_dict())

    assert decrypt_text(key, restored, b"field") == "hello"
