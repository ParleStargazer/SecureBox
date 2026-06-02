"""Flet desktop application shell."""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path

import flet as ft

from securebox.config import DEFAULT_DATA_DIR, DEFAULT_DB_NAME
from securebox.crypto.file_crypto import decrypt_file, encrypt_file
from securebox.db.connection import connect_database
from securebox.db.schema import initialize_schema
from securebox.services.auth_service import AuthService, VaultSession
from securebox.services.clipboard_service import ClipboardAutoClearService
from securebox.services.export_service import export_entries_to_file, import_entries_from_file
from securebox.services.lock_service import IdleLockService
from securebox.services.password_generator import (
    PasswordGeneratorOptions,
    generate_password,
)
from securebox.services.retry_delay_service import RetryDelayService
from securebox.services.strength_service import analyze_password
from securebox.services.text_crypto_service import (
    decrypt_text_with_key,
    decrypt_text_with_password,
    encrypt_text_with_key,
    encrypt_text_with_password,
)
from securebox.services.vault_service import PasswordEntry, PasswordEntryDraft, VaultService
from securebox.ui.theme import apply_theme
from securebox.utils.errors import AuthenticationFailedError, SecureBoxError


@dataclass
class SecureBoxAppState:
    db_path: Path
    connection: sqlite3.Connection
    auth_service: AuthService
    lock_service: IdleLockService
    clipboard_service: ClipboardAutoClearService
    retry_delay_service: RetryDelayService
    session: VaultSession | None = None

    @classmethod
    def create(cls, db_path: str | Path | None = None) -> SecureBoxAppState:
        path = Path(db_path) if db_path is not None else DEFAULT_DATA_DIR / DEFAULT_DB_NAME
        connection = connect_database(path)
        initialize_schema(connection)
        return cls(
            db_path=path,
            connection=connection,
            auth_service=AuthService(connection),
            lock_service=IdleLockService(),
            clipboard_service=ClipboardAutoClearService(),
            retry_delay_service=RetryDelayService(),
        )


class SecureBoxFletApp:
    def __init__(self, page: ft.Page, state: SecureBoxAppState) -> None:
        self.page = page
        self.state = state
        self.vault_service: VaultService | None = None
        self.selected_entry_id: int | None = None

    def render(self) -> None:
        apply_theme(self.page)
        if self.state.session is None:
            self._render_auth()
        else:
            self._render_main()

    def _render_auth(self) -> None:
        initialized = self.state.auth_service.is_initialized()
        password = ft.TextField(
            label="Master password",
            password=True,
            can_reveal_password=True,
            width=360,
            autofocus=True,
        )
        confirm = ft.TextField(
            label="Confirm master password",
            password=True,
            can_reveal_password=True,
            width=360,
            visible=not initialized,
        )

        def submit(_: ft.ControlEvent) -> None:
            try:
                if initialized:
                    self.state.session = self.state.auth_service.login(password.value or "")
                    self.state.retry_delay_service.record_success()
                else:
                    if password.value != confirm.value:
                        self._snack("Master passwords do not match.")
                        return
                    self.state.session = self.state.auth_service.initialize(password.value or "")
                self.state.lock_service.unlock()
                self.vault_service = VaultService(
                    self.state.connection,
                    self.state.session.data_key,
                )
                self.render()
            except AuthenticationFailedError:
                delay = self.state.retry_delay_service.record_failure()
                self._snack(f"Master password is incorrect. Retry delay: {delay:.0f}s.")
            except SecureBoxError as exc:
                self._snack(str(exc))

        self.page.controls.clear()
        self.page.add(
            ft.Container(
                ft.Column(
                    [
                        ft.Icon(ft.Icons.SECURITY, size=58, color=ft.Colors.BLUE_700),
                        ft.Text("SecureBox", size=32, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "Local password manager",
                            size=15,
                            color=ft.Colors.GREY_700,
                        ),
                        password,
                        confirm,
                        ft.FilledButton(
                            "Unlock" if initialized else "Create vault",
                            icon=ft.Icons.LOGIN if initialized else ft.Icons.ADD_CIRCLE,
                            on_click=submit,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=14,
                ),
                alignment=ft.alignment.center,
                expand=True,
            )
        )
        self.page.update()

    def _render_main(self) -> None:
        self.state.lock_service.mark_activity()
        self.page.controls.clear()
        self.page.add(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("SecureBox", size=26, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            ft.OutlinedButton("Lock", icon=ft.Icons.LOCK, on_click=self._lock),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Tabs(
                        selected_index=0,
                        animation_duration=150,
                        expand=True,
                        tabs=[
                            ft.Tab("Vault", icon=ft.Icons.KEY, content=self._vault_tab()),
                            ft.Tab(
                                "Generator",
                                icon=ft.Icons.PASSWORD,
                                content=self._generator_tab(),
                            ),
                            ft.Tab("Text", icon=ft.Icons.TEXT_FIELDS, content=self._text_tab()),
                            ft.Tab("File", icon=ft.Icons.FOLDER, content=self._file_tab()),
                            ft.Tab(
                                "Export",
                                icon=ft.Icons.IMPORT_EXPORT,
                                content=self._export_tab(),
                            ),
                        ],
                    ),
                ],
                expand=True,
            )
        )
        self.page.update()

    def _vault_tab(self) -> ft.Control:
        service = self._vault()
        entries = service.list_entries()
        title = ft.TextField(label="Title", width=220)
        username = ft.TextField(label="Username", width=220)
        password = ft.TextField(
            label="Password",
            width=220,
            password=True,
            can_reveal_password=True,
        )
        url = ft.TextField(label="URL", width=260)
        note = ft.TextField(label="Note", width=360, multiline=True, min_lines=2, max_lines=4)

        def clear_form() -> None:
            self.selected_entry_id = None
            for field in (title, username, password, url, note):
                field.value = ""

        def save(_: ft.ControlEvent) -> None:
            draft = PasswordEntryDraft(
                title=title.value or "",
                username=username.value or "",
                password=password.value or "",
                url=url.value or "",
                note=note.value or "",
            )
            if self.selected_entry_id is None:
                service.create_entry(draft)
                self._snack("Entry created.")
            else:
                service.update_entry(self.selected_entry_id, draft)
                self._snack("Entry updated.")
            self._render_main()

        def fill(entry: PasswordEntry) -> None:
            self.selected_entry_id = entry.id
            title.value = entry.title
            username.value = entry.username
            password.value = entry.password
            url.value = entry.url
            note.value = entry.note
            self.page.update()

        def copy_password(entry: PasswordEntry) -> None:
            self.page.set_clipboard(entry.password)
            self.state.clipboard_service.mark_copied()
            threading.Timer(30.0, lambda: self.page.set_clipboard("")).start()
            self._snack("Password copied. Clipboard will be cleared.")

        def delete(entry: PasswordEntry) -> None:
            service.delete_entry(entry.id)
            self._snack("Entry deleted.")
            self._render_main()

        entry_controls: list[ft.Control] = [
            ft.ListTile(
                title=ft.Text(entry.title),
                subtitle=ft.Text(entry.username),
                leading=ft.Icon(ft.Icons.VPN_KEY),
                trailing=ft.Row(
                    [
                        ft.IconButton(
                            ft.Icons.CONTENT_COPY,
                            on_click=lambda _, item=entry: copy_password(item),
                        ),
                        ft.IconButton(ft.Icons.EDIT, on_click=lambda _, item=entry: fill(item)),
                        ft.IconButton(ft.Icons.DELETE, on_click=lambda _, item=entry: delete(item)),
                    ],
                    tight=True,
                ),
            )
            for entry in entries
        ]
        if not entry_controls:
            entry_controls.append(ft.Text("No entries yet.", color=ft.Colors.GREY_600))

        return ft.Row(
            [
                ft.Container(
                    ft.Column(entry_controls, scroll=ft.ScrollMode.AUTO, spacing=4),
                    expand=True,
                    padding=12,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=8,
                ),
                ft.Container(
                    ft.Column(
                        [
                            title,
                            username,
                            password,
                            url,
                            note,
                            ft.Row(
                                [
                                    ft.FilledButton("Save", icon=ft.Icons.SAVE, on_click=save),
                                    ft.OutlinedButton(
                                        "New",
                                        icon=ft.Icons.ADD,
                                        on_click=lambda _: clear_form(),
                                    ),
                                ]
                            ),
                        ],
                        spacing=10,
                    ),
                    width=390,
                    padding=12,
                ),
            ],
            expand=True,
        )

    def _generator_tab(self) -> ft.Control:
        length = ft.TextField(label="Length", value="20", width=120)
        lower = ft.Checkbox(label="a-z", value=True)
        upper = ft.Checkbox(label="A-Z", value=True)
        digits = ft.Checkbox(label="0-9", value=True)
        symbols = ft.Checkbox(label="Symbols", value=True)
        output = ft.TextField(label="Generated password", width=520, read_only=True)
        strength = ft.Text("", color=ft.Colors.GREY_700)

        def generate(_: ft.ControlEvent) -> None:
            try:
                password = generate_password(
                    PasswordGeneratorOptions(
                        length=int(length.value or "20"),
                        use_lowercase=bool(lower.value),
                        use_uppercase=bool(upper.value),
                        use_digits=bool(digits.value),
                        use_symbols=bool(symbols.value),
                    )
                )
                output.value = password
                score = analyze_password(password)
                strength.value = f"Strength: {score.label} ({score.score}/4)"
                self.page.update()
            except ValueError as exc:
                self._snack(str(exc))

        return ft.Column(
            [
                ft.Row([length, lower, upper, digits, symbols], wrap=True),
                ft.FilledButton("Generate", icon=ft.Icons.AUTO_FIX_HIGH, on_click=generate),
                output,
                strength,
            ],
            spacing=14,
            expand=True,
        )

    def _text_tab(self) -> ft.Control:
        mode = ft.RadioGroup(
            content=ft.Row(
                [
                    ft.Radio(value="session", label="Vault key"),
                    ft.Radio(value="password", label="Text password"),
                ]
            ),
            value="session",
        )
        password = ft.TextField(
            label="Text password",
            password=True,
            can_reveal_password=True,
            width=300,
        )
        input_text = ft.TextField(label="Input", multiline=True, min_lines=5, expand=True)
        output_text = ft.TextField(label="Output", multiline=True, min_lines=5, expand=True)

        def encrypt(_: ft.ControlEvent) -> None:
            if mode.value == "password":
                output_text.value = encrypt_text_with_password(
                    password.value or "",
                    input_text.value or "",
                )
            else:
                output_text.value = encrypt_text_with_key(
                    self._session().data_key,
                    input_text.value or "",
                )
            self.page.update()

        def decrypt(_: ft.ControlEvent) -> None:
            try:
                if mode.value == "password":
                    output_text.value = decrypt_text_with_password(
                        password.value or "",
                        input_text.value or "",
                    )
                else:
                    output_text.value = decrypt_text_with_key(
                        self._session().data_key,
                        input_text.value or "",
                    )
                self.page.update()
            except (AuthenticationFailedError, ValueError) as exc:
                self._snack(str(exc))

        return ft.Column(
            [
                mode,
                password,
                ft.Row([input_text, output_text], expand=True),
                ft.Row(
                    [
                        ft.FilledButton("Encrypt", icon=ft.Icons.LOCK, on_click=encrypt),
                        ft.OutlinedButton("Decrypt", icon=ft.Icons.LOCK_OPEN, on_click=decrypt),
                    ]
                ),
            ],
            spacing=12,
            expand=True,
        )

    def _file_tab(self) -> ft.Control:
        source = ft.TextField(label="Input file path", expand=True)
        target = ft.TextField(label="Output file path", expand=True)
        password = ft.TextField(
            label="File password",
            password=True,
            can_reveal_password=True,
            width=300,
        )
        status = ft.Text("", color=ft.Colors.GREY_700)

        def encrypt(_: ft.ControlEvent) -> None:
            try:
                result = encrypt_file(source.value or "", target.value or "", password.value or "")
                status.value = (
                    f"Encrypted {result.bytes_processed} bytes in {result.chunks} chunks."
                )
                self.page.update()
            except (OSError, ValueError, SecureBoxError) as exc:
                self._snack(str(exc))

        def decrypt(_: ft.ControlEvent) -> None:
            try:
                result = decrypt_file(source.value or "", target.value or "", password.value or "")
                status.value = (
                    f"Decrypted {result.bytes_processed} bytes in {result.chunks} chunks."
                )
                self.page.update()
            except (OSError, ValueError, SecureBoxError) as exc:
                self._snack(str(exc))

        return ft.Column(
            [
                ft.Row([source]),
                ft.Row([target]),
                password,
                ft.Row(
                    [
                        ft.FilledButton("Encrypt file", icon=ft.Icons.LOCK, on_click=encrypt),
                        ft.OutlinedButton(
                            "Decrypt file",
                            icon=ft.Icons.LOCK_OPEN,
                            on_click=decrypt,
                        ),
                    ]
                ),
                status,
            ],
            spacing=12,
            expand=True,
        )

    def _export_tab(self) -> ft.Control:
        path = ft.TextField(label="Export / import file path", expand=True)
        password = ft.TextField(
            label="Export password",
            password=True,
            can_reveal_password=True,
            width=300,
        )
        status = ft.Text("", color=ft.Colors.GREY_700)

        def export(_: ft.ControlEvent) -> None:
            try:
                count = export_entries_to_file(
                    self._vault(),
                    path.value or "",
                    password.value or "",
                )
                status.value = f"Exported {count} encrypted entries."
                self.page.update()
            except (OSError, ValueError, SecureBoxError) as exc:
                self._snack(str(exc))

        def import_entries(_: ft.ControlEvent) -> None:
            try:
                count = import_entries_from_file(
                    self._vault(),
                    path.value or "",
                    password.value or "",
                )
                status.value = f"Imported {count} entries."
                self.page.update()
            except (OSError, ValueError, SecureBoxError) as exc:
                self._snack(str(exc))

        return ft.Column(
            [
                path,
                password,
                ft.Row(
                    [
                        ft.FilledButton("Export", icon=ft.Icons.UPLOAD_FILE, on_click=export),
                        ft.OutlinedButton(
                            "Import",
                            icon=ft.Icons.DOWNLOAD,
                            on_click=import_entries,
                        ),
                    ]
                ),
                status,
            ],
            spacing=12,
            expand=True,
        )

    def _lock(self, _: ft.ControlEvent | None = None) -> None:
        self.state.session = None
        self.vault_service = None
        self.state.lock_service.lock()
        self.render()

    def _vault(self) -> VaultService:
        if self.vault_service is None:
            self.vault_service = VaultService(
                self.state.connection,
                self._session().data_key,
            )
        return self.vault_service

    def _session(self) -> VaultSession:
        if self.state.session is None:
            raise RuntimeError("Vault session is not available")
        return self.state.session

    def _snack(self, message: str) -> None:
        self.page.snack_bar = ft.SnackBar(ft.Text(message))
        self.page.snack_bar.open = True
        self.page.update()


def build_app(page: ft.Page, db_path: str | Path | None = None) -> SecureBoxFletApp:
    state = SecureBoxAppState.create(db_path)
    app = SecureBoxFletApp(page, state)
    app.render()
    return app


def run_app(db_path: str | Path | None = None) -> None:
    """Run the local Flet desktop application.

    SecureBox intentionally does not expose a Web server entry point.
    """
    ft.app(target=lambda page: build_app(page, db_path), view=ft.AppView.FLET_APP)
