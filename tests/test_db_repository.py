import sqlite3

from securebox.config import CRYPTO_VERSION
from securebox.db.connection import connect_database
from securebox.db.repository import (
    ConfigRecord,
    ConfigRepository,
    EncryptedEntryInput,
    PasswordEntryRepository,
)
from securebox.db.schema import SCHEMA_VERSION, initialize_schema
from securebox.utils.time import utc_now_iso


def test_schema_initialization_is_idempotent(tmp_path) -> None:
    db_path = tmp_path / "vault.sqlite3"

    with connect_database(db_path) as connection:
        initialize_schema(connection)
        initialize_schema(connection)
        version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert version == SCHEMA_VERSION


def test_config_repository_save_and_get(tmp_path) -> None:
    with _database(tmp_path) as connection:
        repository = ConfigRepository(connection)
        now = utc_now_iso()
        record = ConfigRecord(
            kdf_name="argon2id",
            kdf_params={"memory_cost": 1024, "time_cost": 1},
            salt="salt",
            encrypted_dek="encrypted-dek",
            verify_blob="verify",
            crypto_version=CRYPTO_VERSION,
            created_at=now,
            updated_at=now,
        )

        repository.save(record)
        loaded = repository.get()

    assert loaded == record


def test_password_entry_repository_crud(tmp_path) -> None:
    with _database(tmp_path) as connection:
        repository = PasswordEntryRepository(connection)
        first = EncryptedEntryInput(
            title_enc="title-1",
            username_enc="username-1",
            password_enc="password-1",
            url_enc="url-1",
            note_enc="note-1",
        )
        second = EncryptedEntryInput(
            title_enc="title-2",
            username_enc="username-2",
            password_enc="password-2",
            url_enc="url-2",
            note_enc="note-2",
        )

        created = repository.create(first)
        updated = repository.update(created.id, second)
        all_entries = repository.list_all()
        deleted = repository.delete(created.id)
        missing = repository.get(created.id)

    assert created.id == 1
    assert created.password_enc == "password-1"
    assert updated is not None
    assert updated.password_enc == "password-2"
    assert len(all_entries) == 1
    assert deleted is True
    assert missing is None


def test_repository_uses_parameterized_queries(tmp_path) -> None:
    malicious_title = "x'); DROP TABLE password_entries; --"

    with _database(tmp_path) as connection:
        repository = PasswordEntryRepository(connection)
        repository.create(
            EncryptedEntryInput(
                title_enc=malicious_title,
                username_enc="username",
                password_enc="password",
                url_enc="url",
                note_enc="note",
            )
        )
        count = connection.execute("SELECT COUNT(*) FROM password_entries").fetchone()[0]

    assert count == 1


def _database(tmp_path) -> sqlite3.Connection:
    connection = connect_database(tmp_path / "vault.sqlite3")
    initialize_schema(connection)
    return connection

