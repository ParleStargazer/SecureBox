"""Chunked file encryption."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from securebox.config import APP_NAME, CRYPTO_VERSION
from securebox.crypto.aead import NONCE_SIZE
from securebox.crypto.kdf import KdfConfig, default_argon2id_config, derive_key
from securebox.utils.errors import AuthenticationFailedError

FILE_MAGIC = b"SecureBoxFile\n"
FILE_PACKAGE_TYPE = "securebox-file"
DEFAULT_CHUNK_SIZE = 64 * 1024
LENGTH_SIZE = 4


@dataclass(frozen=True)
class FileCryptoResult:
    input_path: Path
    output_path: Path
    chunks: int
    bytes_processed: int


def encrypt_file(
    input_path: str | Path,
    output_path: str | Path,
    password: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    kdf_config: KdfConfig | None = None,
) -> FileCryptoResult:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    source = Path(input_path)
    target = Path(output_path)
    config = kdf_config or default_argon2id_config(os.urandom(16))
    key = derive_key(password, config)
    header_bytes = _header_bytes(config, chunk_size)
    chunks = 0
    processed = 0

    with source.open("rb") as input_file, target.open("wb") as output_file:
        output_file.write(FILE_MAGIC)
        output_file.write(_pack_length(len(header_bytes)))
        output_file.write(header_bytes)

        while chunk := input_file.read(chunk_size):
            nonce = os.urandom(NONCE_SIZE)
            aad = _chunk_aad(header_bytes, chunks)
            encrypted = AESGCM(key).encrypt(nonce, chunk, aad)
            output_file.write(nonce)
            output_file.write(_pack_length(len(encrypted)))
            output_file.write(encrypted)
            chunks += 1
            processed += len(chunk)

    return FileCryptoResult(source, target, chunks, processed)


def decrypt_file(
    input_path: str | Path,
    output_path: str | Path,
    password: str,
) -> FileCryptoResult:
    source = Path(input_path)
    target = Path(output_path)
    chunks = 0
    processed = 0

    with source.open("rb") as input_file, target.open("wb") as output_file:
        magic = input_file.read(len(FILE_MAGIC))
        if magic != FILE_MAGIC:
            raise ValueError("Unsupported SecureBox file format")

        header_length = _unpack_length(input_file.read(LENGTH_SIZE))
        header_bytes = input_file.read(header_length)
        header = json.loads(header_bytes.decode())
        if header.get("type") != FILE_PACKAGE_TYPE:
            raise ValueError("Unsupported SecureBox file package")

        key = derive_key(password, KdfConfig.from_dict(header["kdf"]))

        while nonce := input_file.read(NONCE_SIZE):
            if len(nonce) != NONCE_SIZE:
                raise ValueError("Truncated file nonce")
            encrypted_length = _unpack_length(input_file.read(LENGTH_SIZE))
            encrypted = input_file.read(encrypted_length)
            if len(encrypted) != encrypted_length:
                raise ValueError("Truncated encrypted chunk")
            try:
                chunk = AESGCM(key).decrypt(nonce, encrypted, _chunk_aad(header_bytes, chunks))
            except InvalidTag as exc:
                raise AuthenticationFailedError("File chunk failed authentication") from exc
            output_file.write(chunk)
            chunks += 1
            processed += len(chunk)

    return FileCryptoResult(source, target, chunks, processed)


def _header_bytes(config: KdfConfig, chunk_size: int) -> bytes:
    payload = {
        "type": FILE_PACKAGE_TYPE,
        "app": APP_NAME,
        "crypto_version": CRYPTO_VERSION,
        "chunk_size": chunk_size,
        "kdf": config.to_dict(),
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


def _chunk_aad(header_bytes: bytes, chunk_index: int) -> bytes:
    return FILE_MAGIC + header_bytes + chunk_index.to_bytes(8, "big")


def _pack_length(value: int) -> bytes:
    return value.to_bytes(LENGTH_SIZE, "big")


def _unpack_length(data: bytes) -> int:
    if len(data) != LENGTH_SIZE:
        raise ValueError("Truncated length field")
    return int.from_bytes(data, "big")

