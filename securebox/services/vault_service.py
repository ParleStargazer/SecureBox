"""Encrypted password entry service."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from securebox.config import APP_NAME, CRYPTO_VERSION
from securebox.crypto.aead import blob_from_json, blob_to_json, decrypt_text, encrypt_text
from securebox.db.repository import (
    EncryptedEntryInput,
    PasswordEntryRecord,
    PasswordEntryRepository,
)
from securebox.utils.errors import EntryNotFoundError


@dataclass(frozen=True)
class PasswordEntry:
    id: int
    title: str
    username: str
    password: str
    url: str
    note: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class PasswordEntryDraft:
    title: str
    username: str
    password: str
    url: str = ""
    note: str = ""


class VaultService:
    def __init__(self, connection: sqlite3.Connection, data_key: bytes) -> None:
        self._repository = PasswordEntryRepository(connection)
        self._data_key = data_key

    def create_entry(self, draft: PasswordEntryDraft) -> PasswordEntry:
        entry_id = self._repository.next_id()
        encrypted = self._encrypt_draft(entry_id, draft)
        record = self._repository.create(encrypted, entry_id=entry_id)
        return self._decrypt_record(record)

    def list_entries(self) -> list[PasswordEntry]:
        return [self._decrypt_record(record) for record in self._repository.list_all()]

    def get_entry(self, entry_id: int) -> PasswordEntry:
        record = self._repository.get(entry_id)
        if record is None:
            raise EntryNotFoundError(f"Password entry not found: {entry_id}")
        return self._decrypt_record(record)

    def update_entry(self, entry_id: int, draft: PasswordEntryDraft) -> PasswordEntry:
        encrypted = self._encrypt_draft(entry_id, draft)
        record = self._repository.update(entry_id, encrypted)
        if record is None:
            raise EntryNotFoundError(f"Password entry not found: {entry_id}")
        return self._decrypt_record(record)

    def delete_entry(self, entry_id: int) -> bool:
        return self._repository.delete(entry_id)

    def _encrypt_draft(self, entry_id: int, draft: PasswordEntryDraft) -> EncryptedEntryInput:
        return EncryptedEntryInput(
            title_enc=self._encrypt_field(entry_id, "title", draft.title),
            username_enc=self._encrypt_field(entry_id, "username", draft.username),
            password_enc=self._encrypt_field(entry_id, "password", draft.password),
            url_enc=self._encrypt_field(entry_id, "url", draft.url),
            note_enc=self._encrypt_field(entry_id, "note", draft.note),
        )

    def _decrypt_record(self, record: PasswordEntryRecord) -> PasswordEntry:
        return PasswordEntry(
            id=record.id,
            title=self._decrypt_field(record.id, "title", record.title_enc),
            username=self._decrypt_field(record.id, "username", record.username_enc),
            password=self._decrypt_field(record.id, "password", record.password_enc),
            url=self._decrypt_field(record.id, "url", record.url_enc),
            note=self._decrypt_field(record.id, "note", record.note_enc),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _encrypt_field(self, entry_id: int, field_name: str, value: str) -> str:
        return blob_to_json(
            encrypt_text(self._data_key, value, _entry_field_aad(entry_id, field_name))
        )

    def _decrypt_field(self, entry_id: int, field_name: str, payload: str) -> str:
        return decrypt_text(
            self._data_key,
            blob_from_json(payload),
            _entry_field_aad(entry_id, field_name),
        )


def _entry_field_aad(entry_id: int, field_name: str) -> bytes:
    return f"{APP_NAME}:entry:{entry_id}:{field_name}:v{CRYPTO_VERSION}".encode()
