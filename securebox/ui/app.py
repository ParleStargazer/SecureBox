"""Flet desktop application shell."""

from __future__ import annotations

import sqlite3
import threading
import traceback
from dataclasses import dataclass
from inspect import iscoroutinefunction
from pathlib import Path

import flet as ft

from securebox.config import DEFAULT_DB_NAME, get_default_data_dir
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

LanguageCode = str

TRANSLATIONS: dict[LanguageCode, dict[str, str]] = {
    "zh": {
        "subtitle": "本地密码管理器",
        "master_password": "主密码",
        "confirm_master_password": "确认主密码",
        "show_password": "显示密码",
        "unlock": "解锁",
        "create_vault": "创建金库",
        "error_title": "提示",
        "unlock_failed": "解锁失败",
        "password_mismatch": "两次输入的主密码不一致。",
        "password_incorrect_delay": "主密码不正确。重试等待：{delay:.0f} 秒。",
        "switch_language": "Switch to English",
        "help": "帮助",
        "lock": "锁定",
        "vault": "密码",
        "generator": "生成",
        "text": "文本",
        "file": "文件",
        "export": "导出",
        "title": "标题",
        "username": "用户名",
        "password": "密码",
        "url": "URL",
        "note": "备注",
        "entry_created": "条目已创建。",
        "entry_updated": "条目已更新。",
        "password_copied": "密码已复制，剪贴板稍后会自动清空。",
        "entry_deleted": "条目已删除。",
        "copy_password": "复制密码",
        "edit": "编辑",
        "delete": "删除",
        "no_entries": "还没有密码条目。",
        "password_entries": "密码条目",
        "save": "保存",
        "new": "新建",
        "new_entry": "新建密码",
        "edit_entry": "编辑密码",
        "cancel": "取消",
        "length": "长度",
        "symbols": "符号",
        "generated_password": "生成的密码",
        "generate": "生成",
        "strength": "强度：{label} ({score}/4)",
        "vault_key": "金库密钥",
        "text_password": "文本密码",
        "input": "输入",
        "output": "输出",
        "encrypt": "加密",
        "decrypt": "解密",
        "input_file_path": "输入文件路径",
        "output_file_path": "输出文件路径",
        "file_password": "文件密码",
        "encrypt_file": "加密文件",
        "decrypt_file": "解密文件",
        "encrypted_status": "已加密 {bytes_processed} 字节，共 {chunks} 个分块。",
        "decrypted_status": "已解密 {bytes_processed} 字节，共 {chunks} 个分块。",
        "export_import_path": "导出 / 导入文件路径",
        "export_password": "导出密码",
        "exported_status": "已导出 {count} 个加密条目。",
        "imported_status": "已导入 {count} 个条目。",
        "import": "导入",
        "help_title": "SecureBox 使用帮助",
        "close": "关闭",
        "help_auth_title": "初始化与解锁",
        "help_auth_body": (
            "首次使用时输入并确认主密码创建本地金库；"
            "之后用主密码解锁。主密码不会被明文保存。"
        ),
        "help_vault_title": "密码库",
        "help_vault_body": (
            "保存站点、用户名、密码、URL 和备注。"
            "列表中的复制按钮只复制密码，并在 30 秒后清空剪贴板。"
        ),
        "help_generator_title": "密码生成器",
        "help_generator_body": "按长度和字符集生成随机密码，并显示基础强度评分。",
        "help_text_title": "文本加解密",
        "help_text_body": "可使用当前金库密钥或单独文本密码，对短文本进行加密和解密。",
        "help_file_title": "文件加解密",
        "help_file_body": "输入源文件、目标文件和文件密码，对本地文件进行分块加密或解密。",
        "help_export_title": "导入导出",
        "help_export_body": "用导出密码生成加密备份文件，也可以从备份文件导入密码条目。",
    },
    "en": {
        "subtitle": "Local password manager",
        "master_password": "Master password",
        "confirm_master_password": "Confirm master password",
        "show_password": "Show password",
        "unlock": "Unlock",
        "create_vault": "Create vault",
        "error_title": "Notice",
        "unlock_failed": "Unlock failed",
        "password_mismatch": "Master passwords do not match.",
        "password_incorrect_delay": "Master password is incorrect. Retry delay: {delay:.0f}s.",
        "switch_language": "切换到中文",
        "help": "Help",
        "lock": "Lock",
        "vault": "Key",
        "generator": "Gen",
        "text": "Text",
        "file": "File",
        "export": "Exp",
        "title": "Title",
        "username": "Username",
        "password": "Password",
        "url": "URL",
        "note": "Note",
        "entry_created": "Entry created.",
        "entry_updated": "Entry updated.",
        "password_copied": "Password copied. Clipboard will be cleared.",
        "entry_deleted": "Entry deleted.",
        "copy_password": "Copy password",
        "edit": "Edit",
        "delete": "Delete",
        "no_entries": "No entries yet.",
        "password_entries": "Password entries",
        "save": "Save",
        "new": "New",
        "new_entry": "New password",
        "edit_entry": "Edit password",
        "cancel": "Cancel",
        "length": "Length",
        "symbols": "Symbols",
        "generated_password": "Generated password",
        "generate": "Generate",
        "strength": "Strength: {label} ({score}/4)",
        "vault_key": "Vault key",
        "text_password": "Text password",
        "input": "Input",
        "output": "Output",
        "encrypt": "Encrypt",
        "decrypt": "Decrypt",
        "input_file_path": "Input file path",
        "output_file_path": "Output file path",
        "file_password": "File password",
        "encrypt_file": "Encrypt file",
        "decrypt_file": "Decrypt file",
        "encrypted_status": "Encrypted {bytes_processed} bytes in {chunks} chunks.",
        "decrypted_status": "Decrypted {bytes_processed} bytes in {chunks} chunks.",
        "export_import_path": "Export / import file path",
        "export_password": "Export password",
        "exported_status": "Exported {count} encrypted entries.",
        "imported_status": "Imported {count} entries.",
        "import": "Import",
        "help_title": "SecureBox Help",
        "close": "Close",
        "help_auth_title": "Setup and unlock",
        "help_auth_body": (
            "Create the local vault with a master password on first use, "
            "then unlock with it later. The master password is never stored as plaintext."
        ),
        "help_vault_title": "Vault",
        "help_vault_body": (
            "Store a title, username, password, URL, and note. "
            "The copy button copies only the password and clears the clipboard after 30 seconds."
        ),
        "help_generator_title": "Password generator",
        "help_generator_body": (
            "Generate a random password from the selected length and character groups, "
            "with a basic strength score."
        ),
        "help_text_title": "Text encryption",
        "help_text_body": (
            "Encrypt and decrypt short text with either the current vault key "
            "or a separate text password."
        ),
        "help_file_title": "File encryption",
        "help_file_body": (
            "Provide source path, target path, and file password to encrypt "
            "or decrypt local files in chunks."
        ),
        "help_export_title": "Import and export",
        "help_export_body": (
            "Create an encrypted backup with an export password, "
            "or import entries from a backup file."
        ),
    },
}

HELP_SECTION_KEYS = (
    ("help_auth_title", "help_auth_body"),
    ("help_vault_title", "help_vault_body"),
    ("help_generator_title", "help_generator_body"),
    ("help_text_title", "help_text_body"),
    ("help_file_title", "help_file_body"),
    ("help_export_title", "help_export_body"),
)


@dataclass
class SecureBoxAppState:
    db_path: Path
    connection: sqlite3.Connection
    auth_service: AuthService
    lock_service: IdleLockService
    clipboard_service: ClipboardAutoClearService
    retry_delay_service: RetryDelayService
    session: VaultSession | None = None
    language: LanguageCode = "zh"
    selected_tab_index: int = 0

    @classmethod
    def create(cls, db_path: str | Path | None = None) -> SecureBoxAppState:
        path = Path(db_path) if db_path is not None else get_default_data_dir() / DEFAULT_DB_NAME
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

    def _t(self, key: str, **kwargs: object) -> str:
        language = self.state.language if self.state.language in TRANSLATIONS else "zh"
        text = TRANSLATIONS[language].get(key, TRANSLATIONS["en"].get(key, key))
        return text.format(**kwargs)

    def _toggle_language(self, _: ft.ControlEvent | None = None) -> None:
        self.state.language = "en" if self.state.language == "zh" else "zh"
        self.render()

    def _handle_tab_change(self, event: ft.ControlEvent) -> None:
        try:
            self.state.selected_tab_index = int(event.data)
        except (TypeError, ValueError):
            self.state.selected_tab_index = getattr(
                event.control,
                "selected_index",
                self.state.selected_tab_index,
            )

    def _language_button(self) -> ft.Control:
        return ft.IconButton(
            ft.Icons.LANGUAGE,
            tooltip=self._t("switch_language"),
            on_click=self._toggle_language,
            data="language-toggle",
        )

    def _help_button(self) -> ft.Control:
        return ft.IconButton(
            ft.Icons.HELP_OUTLINE,
            tooltip=self._t("help"),
            on_click=self._show_help,
            data="help",
        )

    def _top_actions(self) -> ft.Control:
        return ft.Row(
            [
                ft.Container(expand=True),
                self._language_button(),
                self._help_button(),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _is_desktop(self) -> bool:
        platform = getattr(self.page, "platform", None)
        return platform is None or platform.is_desktop()

    def _lock_button(self) -> ft.Control:
        if self._is_desktop():
            return ft.OutlinedButton(
                self._t("lock"),
                icon=ft.Icons.LOCK,
                on_click=self._lock,
            )
        return ft.IconButton(
            ft.Icons.LOCK,
            tooltip=self._t("lock"),
            on_click=self._lock,
            data="lock",
        )

    def render(self) -> None:
        apply_theme(self.page)
        if self.state.session is None:
            self._render_auth()
        else:
            self._render_main()

    def _render_auth(self) -> None:
        initialized = self.state.auth_service.is_initialized()
        password = ft.TextField(
            label=self._t("master_password"),
            password=True,
            can_reveal_password=False,
            width=360,
            autofocus=True,
        )
        confirm = ft.TextField(
            label=self._t("confirm_master_password"),
            password=True,
            can_reveal_password=False,
            width=360,
            visible=not initialized,
        )
        show_password = ft.Checkbox(label=self._t("show_password"), value=False)

        def toggle_password_visibility(_: ft.ControlEvent) -> None:
            hidden = not bool(show_password.value)
            password.password = hidden
            confirm.password = hidden
            self.page.update()

        show_password.on_change = toggle_password_visibility

        def submit(_: ft.ControlEvent) -> None:
            try:
                if initialized:
                    self.state.session = self.state.auth_service.login(password.value or "")
                    self.state.retry_delay_service.record_success()
                else:
                    if password.value != confirm.value:
                        self._show_message_dialog(
                            self._t("error_title"),
                            self._t("password_mismatch"),
                        )
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
                self._show_message_dialog(
                    self._t("unlock_failed"),
                    self._t("password_incorrect_delay", delay=delay),
                )
            except SecureBoxError as exc:
                self._show_message_dialog(self._t("error_title"), str(exc))

        self.page.controls.clear()
        self.page.add(
            ft.Column(
                [
                    self._top_actions(),
                    ft.Container(
                        ft.Column(
                            [
                                ft.Icon(ft.Icons.SECURITY, size=58, color=ft.Colors.BLUE_700),
                                ft.Text("SecureBox", size=32, weight=ft.FontWeight.BOLD),
                                ft.Text(
                                    self._t("subtitle"),
                                    size=15,
                                    color=ft.Colors.GREY_700,
                                ),
                                password,
                                confirm,
                                show_password,
                                ft.FilledButton(
                                    self._t("unlock")
                                    if initialized
                                    else self._t("create_vault"),
                                    icon=ft.Icons.LOGIN if initialized else ft.Icons.ADD_CIRCLE,
                                    on_click=submit,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=14,
                        ),
                        alignment=ft.Alignment(0, 0),
                        expand=True,
                    ),
                ],
                expand=True,
            )
        )
        self.page.update()

    def _render_main(self) -> None:
        self.state.lock_service.mark_activity()
        tab_items: list[tuple[str, ft.Icons, ft.Control]] = [
            (self._t("vault"), ft.Icons.KEY, self._vault_tab()),
            (self._t("generator"), ft.Icons.PASSWORD, self._generator_tab()),
            (self._t("text"), ft.Icons.TEXT_FIELDS, self._text_tab()),
            (self._t("file"), ft.Icons.FOLDER, self._file_tab()),
            (self._t("export"), ft.Icons.IMPORT_EXPORT, self._export_tab()),
        ]
        self.state.selected_tab_index = min(
            max(self.state.selected_tab_index, 0),
            len(tab_items) - 1,
        )
        self.page.controls.clear()
        self.page.add(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("SecureBox", size=26, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            self._language_button(),
                            self._help_button(),
                            self._lock_button(),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Tabs(
                        length=len(tab_items),
                        selected_index=self.state.selected_tab_index,
                        on_change=self._handle_tab_change,
                        animation_duration=150,
                        expand=True,
                        content=ft.Column(
                            [
                                ft.TabBar(
                                    tabs=[
                                        ft.Tab(label=label, icon=icon)
                                        for label, icon, _ in tab_items
                                    ],
                                    scrollable=False,
                                ),
                                ft.TabBarView(
                                    controls=[
                                        ft.Container(
                                            content,
                                            padding=ft.Padding(0, 28, 0, 0),
                                            expand=True,
                                        )
                                        for _, _, content in tab_items
                                    ],
                                    expand=True,
                                ),
                            ],
                            expand=True,
                            spacing=0,
                        ),
                    ),
                ],
                expand=True,
            )
        )
        self.page.update()

    def _vault_tab(self) -> ft.Control:
        service = self._vault()
        entries = service.list_entries()
        is_desktop = self._is_desktop()

        def open_entry_dialog(entry: PasswordEntry | None = None) -> None:
            title = ft.TextField(
                label=self._t("title"),
                value=entry.title if entry else "",
                data="entry-title",
            )
            username = ft.TextField(
                label=self._t("username"),
                value=entry.username if entry else "",
                data="entry-username",
            )
            password = ft.TextField(
                label=self._t("password"),
                value=entry.password if entry else "",
                password=True,
                can_reveal_password=True,
                data="entry-password",
            )
            url = ft.TextField(
                label=self._t("url"),
                value=entry.url if entry else "",
                data="entry-url",
            )
            note = ft.TextField(
                label=self._t("note"),
                value=entry.note if entry else "",
                multiline=True,
                min_lines=2,
                max_lines=4,
                data="entry-note",
            )

            def save(_: ft.ControlEvent) -> None:
                draft = PasswordEntryDraft(
                    title=title.value or "",
                    username=username.value or "",
                    password=password.value or "",
                    url=url.value or "",
                    note=note.value or "",
                )
                if entry is None:
                    service.create_entry(draft)
                    message = self._t("entry_created")
                else:
                    service.update_entry(entry.id, draft)
                    message = self._t("entry_updated")
                self._close_dialog()
                self._render_main()
                self._snack(message)

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(self._t("new_entry") if entry is None else self._t("edit_entry")),
                content=ft.Column(
                    [title, username, password, url, note],
                    spacing=10,
                    tight=True,
                    width=520 if is_desktop else 320,
                ),
                actions=[
                    ft.TextButton(self._t("cancel"), on_click=lambda _: self._close_dialog()),
                    ft.FilledButton(
                        self._t("save"),
                        icon=ft.Icons.SAVE,
                        on_click=save,
                        data="save-entry",
                    ),
                ],
                scrollable=True,
            )
            self.page.show_dialog(dialog)
            self.page.update()

        def delete(entry: PasswordEntry) -> None:
            service.delete_entry(entry.id)
            self._snack(self._t("entry_deleted"))
            self._render_main()

        def entry_actions(entry: PasswordEntry) -> list[ft.Control]:
            return [
                ft.IconButton(
                    ft.Icons.CONTENT_COPY,
                    tooltip=self._t("copy_password"),
                    on_click=lambda _, item=entry: self._copy_entry_password(item),
                    data="copy-password",
                ),
                ft.IconButton(
                    ft.Icons.EDIT,
                    tooltip=self._t("edit"),
                    on_click=lambda _, item=entry: open_entry_dialog(item),
                    data="edit-entry",
                ),
                ft.IconButton(
                    ft.Icons.DELETE,
                    tooltip=self._t("delete"),
                    on_click=lambda _, item=entry: delete(item),
                ),
            ]

        def entry_control(entry: PasswordEntry) -> ft.Control:
            if is_desktop:
                return ft.ListTile(
                    title=ft.Text(entry.title),
                    subtitle=ft.Text(entry.username),
                    leading=ft.Icon(ft.Icons.VPN_KEY),
                    trailing=ft.Row(entry_actions(entry), tight=True),
                )

            return ft.Row(
                [
                    ft.Icon(ft.Icons.VPN_KEY),
                    ft.Column(
                        [
                            ft.Text(entry.title, weight=ft.FontWeight.BOLD),
                            ft.Text(entry.username, color=ft.Colors.GREY_700),
                        ],
                        expand=True,
                        spacing=2,
                    ),
                    ft.Row(entry_actions(entry), tight=True),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )

        entry_controls: list[ft.Control] = [entry_control(entry) for entry in entries]
        if not entry_controls:
            entry_controls.append(ft.Text(self._t("no_entries"), color=ft.Colors.GREY_600))

        entry_list = ft.Container(
            ft.Column(entry_controls, scroll=ft.ScrollMode.AUTO, spacing=4),
            expand=is_desktop,
            padding=12,
            border=ft.Border(
                top=ft.BorderSide(1, ft.Colors.GREY_300),
                right=ft.BorderSide(1, ft.Colors.GREY_300),
                bottom=ft.BorderSide(1, ft.Colors.GREY_300),
                left=ft.BorderSide(1, ft.Colors.GREY_300),
            ),
            border_radius=8,
        )

        toolbar = ft.Row(
            [
                ft.Text(self._t("password_entries"), size=16, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.FilledButton(
                    self._t("new"),
                    icon=ft.Icons.ADD,
                    on_click=lambda _: open_entry_dialog(),
                    data="new-entry",
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        if not is_desktop:
            return ft.Column(
                [
                    toolbar,
                    entry_list,
                ],
                expand=True,
                spacing=12,
                scroll=ft.ScrollMode.AUTO,
            )

        return ft.Column(
            [
                toolbar,
                entry_list,
            ],
            expand=True,
            spacing=10,
        )

    def _generator_tab(self) -> ft.Control:
        length = ft.TextField(value="20", width=120)
        length_input = ft.Column(
            [
                ft.Text(self._t("length"), size=14, color=ft.Colors.GREY_700),
                length,
            ],
            spacing=4,
        )
        lower = ft.Checkbox(label="a-z", value=True)
        upper = ft.Checkbox(label="A-Z", value=True)
        digits = ft.Checkbox(label="0-9", value=True)
        symbols = ft.Checkbox(label=self._t("symbols"), value=True)
        output = ft.TextField(label=self._t("generated_password"), width=520, read_only=True)
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
                strength.value = self._t("strength", label=score.label, score=score.score)
                self.page.update()
            except ValueError as exc:
                self._snack(str(exc))

        return ft.Column(
            [
                ft.Row([length_input, lower, upper, digits, symbols], wrap=True),
                ft.FilledButton(
                    self._t("generate"),
                    icon=ft.Icons.AUTO_FIX_HIGH,
                    on_click=generate,
                ),
                output,
                strength,
            ],
            spacing=14,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

    def _text_tab(self) -> ft.Control:
        mode = ft.RadioGroup(
            content=ft.Row(
                [
                    ft.Radio(value="session", label=self._t("vault_key")),
                    ft.Radio(value="password", label=self._t("text_password")),
                ]
            ),
            value="session",
        )
        password = ft.TextField(
            label=self._t("text_password"),
            password=True,
            can_reveal_password=True,
            width=300,
        )
        input_text = ft.TextField(label=self._t("input"), multiline=True, min_lines=5, expand=True)
        output_text = ft.TextField(
            label=self._t("output"),
            multiline=True,
            min_lines=5,
            expand=True,
        )

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
                ft.Row([input_text, output_text], expand=True)
                if self._is_desktop()
                else ft.Column([input_text, output_text], spacing=12, expand=True),
                ft.Row(
                    [
                        ft.FilledButton(
                            self._t("encrypt"),
                            icon=ft.Icons.LOCK,
                            on_click=encrypt,
                        ),
                        ft.OutlinedButton(
                            self._t("decrypt"),
                            icon=ft.Icons.LOCK_OPEN,
                            on_click=decrypt,
                        ),
                    ]
                ),
            ],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

    def _file_tab(self) -> ft.Control:
        source = ft.TextField(label=self._t("input_file_path"), expand=True)
        target = ft.TextField(label=self._t("output_file_path"), expand=True)
        password = ft.TextField(
            label=self._t("file_password"),
            password=True,
            can_reveal_password=True,
            width=300,
        )
        status = ft.Text("", color=ft.Colors.GREY_700)

        def encrypt(_: ft.ControlEvent) -> None:
            try:
                result = encrypt_file(source.value or "", target.value or "", password.value or "")
                status.value = self._t(
                    "encrypted_status",
                    bytes_processed=result.bytes_processed,
                    chunks=result.chunks,
                )
                self.page.update()
            except (OSError, ValueError, SecureBoxError) as exc:
                self._snack(str(exc))

        def decrypt(_: ft.ControlEvent) -> None:
            try:
                result = decrypt_file(source.value or "", target.value or "", password.value or "")
                status.value = self._t(
                    "decrypted_status",
                    bytes_processed=result.bytes_processed,
                    chunks=result.chunks,
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
                        ft.FilledButton(
                            self._t("encrypt_file"),
                            icon=ft.Icons.LOCK,
                            on_click=encrypt,
                        ),
                        ft.OutlinedButton(
                            self._t("decrypt_file"),
                            icon=ft.Icons.LOCK_OPEN,
                            on_click=decrypt,
                        ),
                    ]
                ),
                status,
            ],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

    def _export_tab(self) -> ft.Control:
        path = ft.TextField(label=self._t("export_import_path"), expand=True)
        password = ft.TextField(
            label=self._t("export_password"),
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
                status.value = self._t("exported_status", count=count)
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
                status.value = self._t("imported_status", count=count)
                self.page.update()
            except (OSError, ValueError, SecureBoxError) as exc:
                self._snack(str(exc))

        return ft.Column(
            [
                ft.Row([path]),
                password,
                ft.Row(
                    [
                        ft.FilledButton(
                            self._t("export"),
                            icon=ft.Icons.UPLOAD_FILE,
                            on_click=export,
                        ),
                        ft.OutlinedButton(
                            self._t("import"),
                            icon=ft.Icons.DOWNLOAD,
                            on_click=import_entries,
                        ),
                    ]
                ),
                status,
            ],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

    def _lock(self, _: ft.ControlEvent | None = None) -> None:
        self.state.session = None
        self.vault_service = None
        self.state.lock_service.lock()
        self.render()

    def _show_message_dialog(self, title: str, message: str) -> None:
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Text(message, selectable=True),
            actions=[
                ft.TextButton(self._t("close"), on_click=lambda _: self._close_dialog()),
            ],
        )
        self.page.show_dialog(dialog)
        self.page.update()

    def _show_help(self, _: ft.ControlEvent | None = None) -> None:
        sections: list[ft.Control] = []
        for title_key, body_key in HELP_SECTION_KEYS:
            sections.extend(
                [
                    ft.Text(self._t(title_key), weight=ft.FontWeight.BOLD),
                    ft.Text(self._t(body_key), selectable=True),
                ]
            )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(self._t("help_title")),
            content=ft.Column(sections, spacing=8, tight=True, width=520),
            actions=[
                ft.TextButton(self._t("close"), on_click=lambda _: self._close_dialog()),
            ],
            scrollable=True,
        )
        self.page.show_dialog(dialog)

    def _close_dialog(self) -> None:
        self.page.pop_dialog()
        self.page.update()

    def _copy_entry_password(self, entry: PasswordEntry) -> None:
        latest = self._vault().get_entry(entry.id)
        self._set_clipboard(latest.password)
        self.state.clipboard_service.mark_copied()
        timer = threading.Timer(
            self.state.clipboard_service.clear_after_seconds,
            lambda: self._set_clipboard(""),
        )
        timer.daemon = True
        timer.start()
        self._snack(self._t("password_copied"))

    def _set_clipboard(self, value: str) -> None:
        legacy_setter = getattr(self.page, "set_clipboard", None)
        if legacy_setter is not None:
            legacy_setter(value)
            return

        clipboard = getattr(self.page, "clipboard", None)
        setter = getattr(clipboard, "set", None)
        if setter is None:
            return

        if iscoroutinefunction(setter):

            async def set_value() -> None:
                await setter(value)

            self.page.run_task(set_value)
            return

        setter(value)

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


def show_startup_error(page: ft.Page, exc: Exception) -> None:
    page.controls.clear()
    page.add(
        ft.Container(
            ft.Column(
                [
                    ft.Text("SecureBox startup error", size=22, weight=ft.FontWeight.BOLD),
                    ft.Text(str(exc), selectable=True),
                ],
                spacing=12,
            ),
            padding=24,
        )
    )
    page.update()


def run_app(db_path: str | Path | None = None) -> None:
    """Run the local Flet desktop application.

    SecureBox intentionally does not expose a Web server entry point.
    """

    def target(page: ft.Page) -> None:
        try:
            build_app(page, db_path)
        except Exception as exc:
            traceback.print_exc()
            show_startup_error(page, exc)

    ft.app(target=target, view=ft.AppView.FLET_APP)
