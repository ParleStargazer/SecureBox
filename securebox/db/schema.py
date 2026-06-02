"""Database schema initialization."""

from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 1


def initialize_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            kdf_name TEXT NOT NULL,
            kdf_params TEXT NOT NULL,
            salt TEXT NOT NULL,
            encrypted_dek TEXT NOT NULL,
            verify_blob TEXT NOT NULL,
            crypto_version INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS password_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title_enc TEXT NOT NULL,
            username_enc TEXT NOT NULL,
            password_enc TEXT NOT NULL,
            url_enc TEXT NOT NULL,
            note_enc TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            crypto_version INTEGER NOT NULL
        );
        """
    )
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    connection.commit()

