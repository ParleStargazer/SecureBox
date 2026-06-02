"""Vault initialization and authentication service."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass

from securebox.config import CRYPTO_VERSION
from securebox.crypto.aead import blob_from_json, blob_to_json
from securebox.crypto.kdf import KdfConfig, default_argon2id_config, derive_key
from securebox.crypto.keys import (
    create_verify_blob,
    decrypt_data_key,
    encrypt_data_key,
    generate_data_key,
    verify_master_key,
)
from securebox.db.repository import ConfigRecord, ConfigRepository
from securebox.utils.encoding import b64decode, b64encode
from securebox.utils.errors import (
    VaultAlreadyInitializedError,
    VaultNotInitializedError,
)
from securebox.utils.time import utc_now_iso


@dataclass(frozen=True)
class VaultSession:
    data_key: bytes


class AuthService:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._config_repository = ConfigRepository(connection)

    def is_initialized(self) -> bool:
        return self._config_repository.get() is not None

    def initialize(
        self,
        master_password: str,
        kdf_config: KdfConfig | None = None,
    ) -> VaultSession:
        if self.is_initialized():
            raise VaultAlreadyInitializedError("Vault is already initialized")

        config = kdf_config or default_argon2id_config(os.urandom(16))
        kek = derive_key(master_password, config)
        data_key = generate_data_key()
        now = utc_now_iso()

        self._config_repository.save(
            ConfigRecord(
                kdf_name=config.name,
                kdf_params=config.params,
                salt=b64encode(config.salt),
                encrypted_dek=blob_to_json(encrypt_data_key(kek, data_key)),
                verify_blob=blob_to_json(create_verify_blob(kek)),
                crypto_version=CRYPTO_VERSION,
                created_at=now,
                updated_at=now,
            )
        )
        return VaultSession(data_key=data_key)

    def login(self, master_password: str) -> VaultSession:
        record = self._load_config()
        kdf_config = _kdf_config_from_record(record)
        kek = derive_key(master_password, kdf_config)
        verify_master_key(kek, blob_from_json(record.verify_blob))
        data_key = decrypt_data_key(kek, blob_from_json(record.encrypted_dek))
        return VaultSession(data_key=data_key)

    def change_master_password(
        self,
        session: VaultSession,
        new_master_password: str,
        kdf_config: KdfConfig | None = None,
    ) -> VaultSession:
        record = self._load_config()
        config = kdf_config or default_argon2id_config(os.urandom(16))
        kek = derive_key(new_master_password, config)
        now = utc_now_iso()

        self._config_repository.save(
            ConfigRecord(
                kdf_name=config.name,
                kdf_params=config.params,
                salt=b64encode(config.salt),
                encrypted_dek=blob_to_json(encrypt_data_key(kek, session.data_key)),
                verify_blob=blob_to_json(create_verify_blob(kek)),
                crypto_version=CRYPTO_VERSION,
                created_at=record.created_at,
                updated_at=now,
            )
        )
        return VaultSession(data_key=session.data_key)

    def _load_config(self) -> ConfigRecord:
        record = self._config_repository.get()
        if record is None:
            raise VaultNotInitializedError("Vault is not initialized")
        return record


def _kdf_config_from_record(record: ConfigRecord) -> KdfConfig:
    return KdfConfig(
        name=record.kdf_name,
        salt=b64decode(record.salt),
        params=record.kdf_params,
    )

