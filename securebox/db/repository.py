"""Repository classes for SQLite persistence."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any

from securebox.config import CRYPTO_VERSION
from securebox.utils.time import utc_now_iso


@dataclass(frozen=True)
class ConfigRecord:
    kdf_name: str
    kdf_params: dict[str, Any]
    salt: str
    encrypted_dek: str
    verify_blob: str
    crypto_version: int
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class PasswordEntryRecord:
    id: int
    title_enc: str
    username_enc: str
    password_enc: str
    url_enc: str
    note_enc: str
    created_at: str
    updated_at: str
    crypto_version: int


@dataclass(frozen=True)
class EncryptedEntryInput:
    title_enc: str
    username_enc: str
    password_enc: str
    url_enc: str
    note_enc: str


class ConfigRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get(self) -> ConfigRecord | None:
        row = self._connection.execute("SELECT * FROM config WHERE id = ?", (1,)).fetchone()
        if row is None:
            return None
        return _config_from_row(row)

    def save(self, record: ConfigRecord) -> None:
        self._connection.execute(
            """
            INSERT INTO config (
                id, kdf_name, kdf_params, salt, encrypted_dek, verify_blob,
                crypto_version, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                kdf_name = excluded.kdf_name,
                kdf_params = excluded.kdf_params,
                salt = excluded.salt,
                encrypted_dek = excluded.encrypted_dek,
                verify_blob = excluded.verify_blob,
                crypto_version = excluded.crypto_version,
                updated_at = excluded.updated_at
            """,
            (
                1,
                record.kdf_name,
                json.dumps(record.kdf_params, separators=(",", ":")),
                record.salt,
                record.encrypted_dek,
                record.verify_blob,
                record.crypto_version,
                record.created_at,
                record.updated_at,
            ),
        )
        self._connection.commit()


class PasswordEntryRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def create(self, entry: EncryptedEntryInput) -> PasswordEntryRecord:
        now = utc_now_iso()
        cursor = self._connection.execute(
            """
            INSERT INTO password_entries (
                title_enc, username_enc, password_enc, url_enc, note_enc,
                created_at, updated_at, crypto_version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.title_enc,
                entry.username_enc,
                entry.password_enc,
                entry.url_enc,
                entry.note_enc,
                now,
                now,
                CRYPTO_VERSION,
            ),
        )
        self._connection.commit()
        created_id = int(cursor.lastrowid)
        record = self.get(created_id)
        if record is None:
            raise RuntimeError("Created password entry could not be loaded")
        return record

    def list_all(self) -> list[PasswordEntryRecord]:
        rows = self._connection.execute(
            "SELECT * FROM password_entries ORDER BY id ASC"
        ).fetchall()
        return [_entry_from_row(row) for row in rows]

    def get(self, entry_id: int) -> PasswordEntryRecord | None:
        row = self._connection.execute(
            "SELECT * FROM password_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        if row is None:
            return None
        return _entry_from_row(row)

    def update(self, entry_id: int, entry: EncryptedEntryInput) -> PasswordEntryRecord | None:
        now = utc_now_iso()
        cursor = self._connection.execute(
            """
            UPDATE password_entries
            SET title_enc = ?,
                username_enc = ?,
                password_enc = ?,
                url_enc = ?,
                note_enc = ?,
                updated_at = ?,
                crypto_version = ?
            WHERE id = ?
            """,
            (
                entry.title_enc,
                entry.username_enc,
                entry.password_enc,
                entry.url_enc,
                entry.note_enc,
                now,
                CRYPTO_VERSION,
                entry_id,
            ),
        )
        self._connection.commit()
        if cursor.rowcount == 0:
            return None
        return self.get(entry_id)

    def delete(self, entry_id: int) -> bool:
        cursor = self._connection.execute(
            "DELETE FROM password_entries WHERE id = ?", (entry_id,)
        )
        self._connection.commit()
        return cursor.rowcount > 0


def _config_from_row(row: sqlite3.Row) -> ConfigRecord:
    return ConfigRecord(
        kdf_name=row["kdf_name"],
        kdf_params=json.loads(row["kdf_params"]),
        salt=row["salt"],
        encrypted_dek=row["encrypted_dek"],
        verify_blob=row["verify_blob"],
        crypto_version=row["crypto_version"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _entry_from_row(row: sqlite3.Row) -> PasswordEntryRecord:
    return PasswordEntryRecord(
        id=row["id"],
        title_enc=row["title_enc"],
        username_enc=row["username_enc"],
        password_enc=row["password_enc"],
        url_enc=row["url_enc"],
        note_enc=row["note_enc"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        crypto_version=row["crypto_version"],
    )

