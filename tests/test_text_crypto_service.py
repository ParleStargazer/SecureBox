import os

import pytest

from securebox.crypto.kdf import KdfConfig
from securebox.services.text_crypto_service import (
    decrypt_text_with_key,
    decrypt_text_with_password,
    encrypt_text_with_key,
    encrypt_text_with_password,
)
from securebox.utils.errors import AuthenticationFailedError


def test_text_crypto_with_session_key_roundtrip() -> None:
    data_key = os.urandom(32)

    payload = encrypt_text_with_key(data_key, "hello securebox")

    assert "hello securebox" not in payload
    assert decrypt_text_with_key(data_key, payload) == "hello securebox"


def test_text_crypto_with_session_key_detects_wrong_key() -> None:
    payload = encrypt_text_with_key(os.urandom(32), "secret")

    with pytest.raises(AuthenticationFailedError):
        decrypt_text_with_key(os.urandom(32), payload)


def test_text_crypto_with_password_roundtrip() -> None:
    payload = encrypt_text_with_password("text-password", "private text", fast_argon2_config())

    assert "private text" not in payload
    assert decrypt_text_with_password("text-password", payload) == "private text"


def test_text_crypto_with_password_rejects_wrong_password() -> None:
    payload = encrypt_text_with_password("right-password", "private text", fast_argon2_config())

    with pytest.raises(AuthenticationFailedError):
        decrypt_text_with_password("wrong-password", payload)


def fast_argon2_config() -> KdfConfig:
    return KdfConfig(
        name="argon2id",
        salt=os.urandom(16),
        params={
            "memory_cost": 1024,
            "time_cost": 1,
            "parallelism": 1,
            "hash_len": 32,
        },
    )

