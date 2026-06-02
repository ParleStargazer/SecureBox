import os

import pytest

from securebox.crypto.kdf import KdfConfig
from securebox.db.connection import connect_database
from securebox.db.repository import PasswordEntryRepository
from securebox.db.schema import initialize_schema
from securebox.services.auth_service import AuthService
from securebox.services.vault_service import PasswordEntryDraft, VaultService
from securebox.utils.errors import AuthenticationFailedError, EntryNotFoundError


def test_vault_creates_encrypted_entry_without_plaintext_in_database(tmp_path) -> None:
    with _database(tmp_path) as connection:
        session = AuthService(connection).initialize("master", fast_argon2_config())
        service = VaultService(connection, session.data_key)

        entry = service.create_entry(
            PasswordEntryDraft(
                title="Email",
                username="alice",
                password="correct-horse",
                url="https://example.com",
                note="private note",
            )
        )
        raw_record = PasswordEntryRepository(connection).get(entry.id)

    assert entry.title == "Email"
    assert entry.password == "correct-horse"
    assert raw_record is not None
    raw_values = " ".join(
        [
            raw_record.title_enc,
            raw_record.username_enc,
            raw_record.password_enc,
            raw_record.url_enc,
            raw_record.note_enc,
        ]
    )
    assert "correct-horse" not in raw_values
    assert "private note" not in raw_values


def test_vault_lists_updates_and_deletes_entries(tmp_path) -> None:
    with _database(tmp_path) as connection:
        session = AuthService(connection).initialize("master", fast_argon2_config())
        service = VaultService(connection, session.data_key)
        created = service.create_entry(PasswordEntryDraft("Email", "alice", "old"))

        updated = service.update_entry(
            created.id,
            PasswordEntryDraft("Email", "alice", "new", "https://example.com", "changed"),
        )
        listed = service.list_entries()
        deleted = service.delete_entry(created.id)

        with pytest.raises(EntryNotFoundError):
            service.get_entry(created.id)

    assert updated.password == "new"
    assert updated.note == "changed"
    assert listed[0].password == "new"
    assert deleted is True


def test_vault_detects_field_replacement_attack(tmp_path) -> None:
    with _database(tmp_path) as connection:
        session = AuthService(connection).initialize("master", fast_argon2_config())
        service = VaultService(connection, session.data_key)
        entry = service.create_entry(PasswordEntryDraft("Email", "alice", "secret"))
        repository = PasswordEntryRepository(connection)
        raw = repository.get(entry.id)
        assert raw is not None
        repository.update(
            entry.id,
            raw.__class__(
                id=raw.id,
                title_enc=raw.password_enc,
                username_enc=raw.username_enc,
                password_enc=raw.password_enc,
                url_enc=raw.url_enc,
                note_enc=raw.note_enc,
                created_at=raw.created_at,
                updated_at=raw.updated_at,
                crypto_version=raw.crypto_version,
            ),
        )

        with pytest.raises(AuthenticationFailedError):
            service.get_entry(entry.id)


def _database(tmp_path):
    connection = connect_database(tmp_path / "vault.sqlite3")
    initialize_schema(connection)
    return connection


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
