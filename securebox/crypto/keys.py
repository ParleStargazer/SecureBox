"""Helpers for DEK/KEK handling."""

from __future__ import annotations

import os

from securebox.config import APP_NAME, CRYPTO_VERSION
from securebox.crypto.aead import EncryptedBlob, decrypt_bytes, encrypt_bytes

DATA_KEY_SIZE = 32
VERIFY_PLAINTEXT = f"{APP_NAME} verification v{CRYPTO_VERSION}".encode()


def generate_data_key() -> bytes:
    return os.urandom(DATA_KEY_SIZE)


def key_wrap_aad(label: str) -> bytes:
    return f"{APP_NAME}:key-wrap:{label}:v{CRYPTO_VERSION}".encode()


def verification_aad() -> bytes:
    return f"{APP_NAME}:verify:v{CRYPTO_VERSION}".encode()


def encrypt_data_key(kek: bytes, data_key: bytes) -> EncryptedBlob:
    _validate_data_key(data_key)
    return encrypt_bytes(kek, data_key, key_wrap_aad("data-key"))


def decrypt_data_key(kek: bytes, encrypted_data_key: EncryptedBlob) -> bytes:
    data_key = decrypt_bytes(kek, encrypted_data_key, key_wrap_aad("data-key"))
    _validate_data_key(data_key)
    return data_key


def create_verify_blob(kek: bytes) -> EncryptedBlob:
    return encrypt_bytes(kek, VERIFY_PLAINTEXT, verification_aad())


def verify_master_key(kek: bytes, verify_blob: EncryptedBlob) -> bool:
    return decrypt_bytes(kek, verify_blob, verification_aad()) == VERIFY_PLAINTEXT


def _validate_data_key(data_key: bytes) -> None:
    if len(data_key) != DATA_KEY_SIZE:
        raise ValueError("Data encryption key must be 32 bytes")
