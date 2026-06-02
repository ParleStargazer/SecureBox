"""Key derivation helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from securebox.utils.encoding import b64decode, b64encode

KdfName = Literal["argon2id", "pbkdf2-sha256"]
KEY_LENGTH = 32


@dataclass(frozen=True)
class KdfConfig:
    name: KdfName
    salt: bytes
    params: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "salt": b64encode(self.salt),
            "params": dict(self.params),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> KdfConfig:
        return cls(
            name=payload["name"],
            salt=b64decode(payload["salt"]),
            params={key: int(value) for key, value in payload.get("params", {}).items()},
        )


def default_argon2id_config(salt: bytes) -> KdfConfig:
    return KdfConfig(
        name="argon2id",
        salt=salt,
        params={
            "memory_cost": 64 * 1024,
            "time_cost": 3,
            "parallelism": 1,
            "hash_len": KEY_LENGTH,
        },
    )


def default_pbkdf2_config(salt: bytes) -> KdfConfig:
    return KdfConfig(
        name="pbkdf2-sha256",
        salt=salt,
        params={
            "iterations": 600_000,
            "length": KEY_LENGTH,
        },
    )


def derive_key(master_password: str | bytes, config: KdfConfig) -> bytes:
    password = _password_bytes(master_password)
    if config.name == "argon2id":
        return _derive_argon2id(password, config)
    if config.name == "pbkdf2-sha256":
        return _derive_pbkdf2(password, config)
    raise ValueError(f"Unsupported KDF: {config.name}")


def _password_bytes(master_password: str | bytes) -> bytes:
    if isinstance(master_password, bytes):
        return master_password
    return master_password.encode("utf-8")


def _derive_argon2id(password: bytes, config: KdfConfig) -> bytes:
    return hash_secret_raw(
        secret=password,
        salt=config.salt,
        time_cost=config.params.get("time_cost", 3),
        memory_cost=config.params.get("memory_cost", 64 * 1024),
        parallelism=config.params.get("parallelism", 1),
        hash_len=config.params.get("hash_len", KEY_LENGTH),
        type=Type.ID,
    )


def _derive_pbkdf2(password: bytes, config: KdfConfig) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=config.params.get("length", KEY_LENGTH),
        salt=config.salt,
        iterations=config.params.get("iterations", 600_000),
    )
    return kdf.derive(password)
