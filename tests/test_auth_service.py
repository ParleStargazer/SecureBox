import json
import os

import pytest

from securebox.crypto.kdf import KdfConfig
from securebox.db.connection import connect_database
from securebox.db.repository import ConfigRepository
from securebox.db.schema import initialize_schema
from securebox.services.auth_service import AuthService
from securebox.utils.errors import (
    AuthenticationFailedError,
    VaultAlreadyInitializedError,
    VaultNotInitializedError,
)


def test_auth_initialize_and_login(tmp_path) -> None:
    with _database(tmp_path) as connection:
        service = AuthService(connection)

        initialized = service.initialize("master", fast_argon2_config())
        logged_in = service.login("master")

    assert initialized.data_key == logged_in.data_key


def test_auth_rejects_login_before_initialization(tmp_path) -> None:
    with _database(tmp_path) as connection:
        service = AuthService(connection)

        with pytest.raises(VaultNotInitializedError):
            service.login("master")


def test_auth_rejects_second_initialization(tmp_path) -> None:
    with _database(tmp_path) as connection:
        service = AuthService(connection)
        service.initialize("master", fast_argon2_config())

        with pytest.raises(VaultAlreadyInitializedError):
            service.initialize("master", fast_argon2_config())


def test_auth_rejects_wrong_master_password(tmp_path) -> None:
    with _database(tmp_path) as connection:
        service = AuthService(connection)
        service.initialize("master", fast_argon2_config())

        with pytest.raises(AuthenticationFailedError):
            service.login("wrong")


def test_auth_detects_tampered_verify_blob(tmp_path) -> None:
    with _database(tmp_path) as connection:
        service = AuthService(connection)
        service.initialize("master", fast_argon2_config())
        repository = ConfigRepository(connection)
        record = repository.get()
        assert record is not None
        tampered_verify = json.loads(record.verify_blob)
        tampered_verify["tag"] = _flip_text_byte(tampered_verify["tag"])
        repository.save(
            record.__class__(
                **{
                    **record.__dict__,
                    "verify_blob": json.dumps(tampered_verify, separators=(",", ":")),
                }
            )
        )

        with pytest.raises(AuthenticationFailedError):
            service.login("master")


def test_auth_changes_master_password_without_changing_data_key(tmp_path) -> None:
    with _database(tmp_path) as connection:
        service = AuthService(connection)
        session = service.initialize("old", fast_argon2_config())
        rotated = service.change_master_password(session, "new", fast_argon2_config())

        with pytest.raises(AuthenticationFailedError):
            service.login("old")
        logged_in = service.login("new")

    assert rotated.data_key == session.data_key
    assert logged_in.data_key == session.data_key


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


def _flip_text_byte(value: str) -> str:
    replacement = "A" if value[0] != "A" else "B"
    return replacement + value[1:]


def _database(tmp_path):
    connection = connect_database(tmp_path / "vault.sqlite3")
    initialize_schema(connection)
    return connection
