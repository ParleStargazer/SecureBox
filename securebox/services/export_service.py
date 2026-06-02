"""Encrypted vault export and import."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from securebox.services.text_crypto_service import (
    decrypt_text_with_password,
    encrypt_text_with_password,
)
from securebox.services.vault_service import PasswordEntryDraft, VaultService


def export_entries_to_file(
    vault_service: VaultService,
    output_path: str | Path,
    export_password: str,
) -> int:
    entries = vault_service.list_entries()
    payload: list[dict[str, Any]] = [
        {
            "title": entry.title,
            "username": entry.username,
            "password": entry.password,
            "url": entry.url,
            "note": entry.note,
        }
        for entry in entries
    ]
    encrypted_payload = encrypt_text_with_password(
        export_password,
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    )
    Path(output_path).write_text(encrypted_payload, encoding="utf-8")
    return len(entries)


def import_entries_from_file(
    vault_service: VaultService,
    input_path: str | Path,
    export_password: str,
) -> int:
    encrypted_payload = Path(input_path).read_text(encoding="utf-8")
    payload = json.loads(decrypt_text_with_password(export_password, encrypted_payload))
    for item in payload:
        vault_service.create_entry(
            PasswordEntryDraft(
                title=item.get("title", ""),
                username=item.get("username", ""),
                password=item.get("password", ""),
                url=item.get("url", ""),
                note=item.get("note", ""),
            )
        )
    return len(payload)

