import os

import pytest

from securebox.crypto.aead import decrypt_bytes
from securebox.crypto.kdf import KdfConfig, derive_key
from securebox.crypto.keys import (
    create_verify_blob,
    decrypt_data_key,
    encrypt_data_key,
    generate_data_key,
    verify_master_key,
)
from securebox.utils.errors import AuthenticationFailedError


def fast_argon2_config(salt: bytes) -> KdfConfig:
    return KdfConfig(
        name="argon2id",
        salt=salt,
        params={
            "memory_cost": 1024,
            "time_cost": 1,
            "parallelism": 1,
            "hash_len": 32,
        },
    )


def fast_pbkdf2_config(salt: bytes) -> KdfConfig:
    return KdfConfig(
        name="pbkdf2-sha256",
        salt=salt,
        params={
            "iterations": 1000,
            "length": 32,
        },
    )


@pytest.mark.parametrize("config_factory", [fast_argon2_config, fast_pbkdf2_config])
def test_kdf_derives_stable_key_for_same_inputs(config_factory) -> None:
    config = config_factory(os.urandom(16))

    first = derive_key("correct horse battery staple", config)
    second = derive_key("correct horse battery staple", KdfConfig.from_dict(config.to_dict()))

    assert first == second
    assert len(first) == 32


def test_kdf_salt_changes_key() -> None:
    first = derive_key("password", fast_argon2_config(os.urandom(16)))
    second = derive_key("password", fast_argon2_config(os.urandom(16)))

    assert first != second


def test_data_key_wrap_roundtrip_and_rotation() -> None:
    old_kek = derive_key("old master", fast_argon2_config(os.urandom(16)))
    new_kek = derive_key("new master", fast_argon2_config(os.urandom(16)))
    data_key = generate_data_key()

    encrypted_data_key = encrypt_data_key(old_kek, data_key)
    unwrapped = decrypt_data_key(old_kek, encrypted_data_key)
    rotated = encrypt_data_key(new_kek, unwrapped)

    assert decrypt_data_key(new_kek, rotated) == data_key
    with pytest.raises(AuthenticationFailedError):
        decrypt_data_key(old_kek, rotated)


def test_verify_blob_accepts_correct_key_only() -> None:
    kek = derive_key("master", fast_argon2_config(os.urandom(16)))
    wrong_kek = derive_key("wrong", fast_argon2_config(os.urandom(16)))
    verify_blob = create_verify_blob(kek)

    assert verify_master_key(kek, verify_blob) is True
    with pytest.raises(AuthenticationFailedError):
        verify_master_key(wrong_kek, verify_blob)


def test_key_wrap_aad_prevents_direct_unwrap_without_expected_context() -> None:
    kek = derive_key("master", fast_argon2_config(os.urandom(16)))
    data_key = generate_data_key()
    encrypted_data_key = encrypt_data_key(kek, data_key)

    with pytest.raises(AuthenticationFailedError):
        decrypt_bytes(kek, encrypted_data_key, b"wrong-context")

