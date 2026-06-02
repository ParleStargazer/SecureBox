import os
from pathlib import Path

import pytest

from securebox.crypto.aead import NONCE_SIZE
from securebox.crypto.file_crypto import (
    FILE_MAGIC,
    LENGTH_SIZE,
    decrypt_file,
    encrypt_file,
)
from securebox.crypto.kdf import KdfConfig
from securebox.utils.errors import AuthenticationFailedError


def test_file_crypto_roundtrip(tmp_path) -> None:
    plain = tmp_path / "plain.txt"
    encrypted = tmp_path / "plain.txt.sbox"
    restored = tmp_path / "restored.txt"
    plain.write_bytes(b"hello securebox file crypto" * 10)

    encrypted_result = encrypt_file(
        plain,
        encrypted,
        "file-password",
        chunk_size=11,
        kdf_config=fast_argon2_config(),
    )
    decrypted_result = decrypt_file(encrypted, restored, "file-password")

    assert encrypted_result.chunks > 1
    assert decrypted_result.bytes_processed == plain.stat().st_size
    assert restored.read_bytes() == plain.read_bytes()


def test_file_crypto_rejects_wrong_password(tmp_path) -> None:
    plain, encrypted, restored = _paths(tmp_path)
    plain.write_bytes(b"private data")
    encrypt_file(plain, encrypted, "right", chunk_size=4, kdf_config=fast_argon2_config())

    with pytest.raises(AuthenticationFailedError):
        decrypt_file(encrypted, restored, "wrong")


def test_file_crypto_detects_tampered_chunk(tmp_path) -> None:
    plain, encrypted, restored = _paths(tmp_path)
    plain.write_bytes(b"private data")
    encrypt_file(plain, encrypted, "password", chunk_size=4, kdf_config=fast_argon2_config())
    payload = bytearray(encrypted.read_bytes())
    payload[-1] ^= 1
    encrypted.write_bytes(payload)

    with pytest.raises(AuthenticationFailedError):
        decrypt_file(encrypted, restored, "password")


def test_file_crypto_detects_chunk_reordering(tmp_path) -> None:
    plain, encrypted, restored = _paths(tmp_path)
    plain.write_bytes(b"abcdefghijklmnopqrstuvwxyz")
    encrypt_file(plain, encrypted, "password", chunk_size=5, kdf_config=fast_argon2_config())

    prefix, chunks = _read_encrypted_chunks(encrypted)
    assert len(chunks) > 2
    chunks[0], chunks[1] = chunks[1], chunks[0]
    encrypted.write_bytes(prefix + b"".join(chunks))

    with pytest.raises(AuthenticationFailedError):
        decrypt_file(encrypted, restored, "password")


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


def _paths(tmp_path) -> tuple[Path, Path, Path]:
    return tmp_path / "plain.bin", tmp_path / "encrypted.sbox", tmp_path / "restored.bin"


def _read_encrypted_chunks(path: Path) -> tuple[bytes, list[bytes]]:
    data = path.read_bytes()
    offset = len(FILE_MAGIC)
    header_length = int.from_bytes(data[offset : offset + LENGTH_SIZE], "big")
    offset += LENGTH_SIZE + header_length
    prefix = data[:offset]
    chunks = []

    while offset < len(data):
        chunk_start = offset
        offset += NONCE_SIZE
        encrypted_length = int.from_bytes(data[offset : offset + LENGTH_SIZE], "big")
        offset += LENGTH_SIZE + encrypted_length
        chunks.append(data[chunk_start:offset])

    return prefix, chunks

