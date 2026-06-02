import os

import pytest

from securebox.crypto.kdf import KdfConfig
from securebox.db.connection import connect_database
from securebox.db.schema import initialize_schema
from securebox.services.auth_service import AuthService
from securebox.services.export_service import export_entries_to_file, import_entries_from_file
from securebox.services.vault_service import PasswordEntryDraft, VaultService
from securebox.utils.errors import AuthenticationFailedError


def test_export_file_is_encrypted_and_importable(tmp_path) -> None:
    export_path = tmp_path / "vault-export.sbox"
    with _database(tmp_path, "source.sqlite3") as source_connection:
        session = AuthService(source_connection).initialize("master", fast_argon2_config())
        source_vault = VaultService(source_connection, session.data_key)
        source_vault.create_entry(
            PasswordEntryDraft(
                title="Email",
                username="alice",
                password="secret-password",
                url="https://example.com",
                note="private note",
            )
        )

        exported = export_entries_to_file(source_vault, export_path, "export-password")

    export_text = export_path.read_text(encoding="utf-8")
    assert exported == 1
    assert "secret-password" not in export_text
    assert "private note" not in export_text

    with _database(tmp_path, "target.sqlite3") as target_connection:
        session = AuthService(target_connection).initialize("master", fast_argon2_config())
        target_vault = VaultService(target_connection, session.data_key)

        imported = import_entries_from_file(target_vault, export_path, "export-password")
        entries = target_vault.list_entries()

    assert imported == 1
    assert entries[0].password == "secret-password"
    assert entries[0].note == "private note"


def test_import_rejects_wrong_export_password(tmp_path) -> None:
    export_path = tmp_path / "vault-export.sbox"
    with _database(tmp_path, "source.sqlite3") as source_connection:
        session = AuthService(source_connection).initialize("master", fast_argon2_config())
        source_vault = VaultService(source_connection, session.data_key)
        source_vault.create_entry(PasswordEntryDraft("Email", "alice", "secret"))
        export_entries_to_file(source_vault, export_path, "right")

    with _database(tmp_path, "target.sqlite3") as target_connection:
        session = AuthService(target_connection).initialize("master", fast_argon2_config())
        target_vault = VaultService(target_connection, session.data_key)

        with pytest.raises(AuthenticationFailedError):
            import_entries_from_file(target_vault, export_path, "wrong")


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


def _database(tmp_path, name):
    connection = connect_database(tmp_path / name)
    initialize_schema(connection)
    return connection

