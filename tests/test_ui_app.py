import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace

import flet as ft

from securebox.config import DEFAULT_DB_NAME, get_default_data_dir
from securebox.services.vault_service import PasswordEntryDraft, VaultService
from securebox.ui.app import SecureBoxAppState, SecureBoxFletApp, build_app
from securebox.ui.theme import apply_theme


class FakePage:
    def __init__(self, platform=None) -> None:
        self.controls = []
        self.clipboard = ""
        self.dialogs = []
        self.platform = platform
        self.window = SimpleNamespace()
        self.updated = 0

    def add(self, *controls) -> None:
        self.controls.extend(controls)

    def update(self) -> None:
        self.updated += 1

    def set_clipboard(self, value: str) -> None:
        self.clipboard = value

    def show_dialog(self, dialog) -> None:
        self.dialogs.append(dialog)

    def pop_dialog(self):
        return self.dialogs.pop() if self.dialogs else None


class FakeClipboard:
    def __init__(self) -> None:
        self.values = []

    async def set(self, value: str) -> None:
        self.values.append(value)


class FakeModernPage:
    def __init__(self, platform=None) -> None:
        self.controls = []
        self.clipboard = FakeClipboard()
        self.dialogs = []
        self.platform = platform
        self.window = SimpleNamespace()
        self.updated = 0

    def add(self, *controls) -> None:
        self.controls.extend(controls)

    def update(self) -> None:
        self.updated += 1

    def show_dialog(self, dialog) -> None:
        self.dialogs.append(dialog)

    def pop_dialog(self):
        return self.dialogs.pop() if self.dialogs else None

    def run_task(self, handler, *args, **kwargs):
        return asyncio.run(handler(*args, **kwargs))


def iter_controls(control):
    yield control
    for attr in ("controls", "content", "title", "subtitle", "leading", "trailing", "actions"):
        value = getattr(control, attr, None)
        if value is None or isinstance(value, str):
            continue
        if isinstance(value, list):
            for child in value:
                yield from iter_controls(child)
        else:
            yield from iter_controls(value)


def find_controls(page: FakePage, control_type: type) -> list:
    found = []
    for control in [*page.controls, *page.dialogs]:
        found.extend(item for item in iter_controls(control) if isinstance(item, control_type))
    return found


def test_app_state_initializes_local_database(tmp_path) -> None:
    db_path = tmp_path / "securebox.sqlite3"

    state = SecureBoxAppState.create(db_path)

    assert state.db_path == db_path
    assert state.auth_service.is_initialized() is False


def test_android_uses_flet_private_storage(monkeypatch, tmp_path) -> None:
    app_storage = tmp_path / "app_storage"
    monkeypatch.setenv("FLET_PLATFORM", "android")
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(app_storage))

    state = SecureBoxAppState.create()

    assert get_default_data_dir() == app_storage
    assert state.db_path == app_storage / DEFAULT_DB_NAME


def test_mobile_theme_skips_window_sizing() -> None:
    page = FakePage(platform=ft.PagePlatform.ANDROID)

    apply_theme(page)

    assert not hasattr(page.window, "width")
    assert not hasattr(page.window, "height")


def test_flet_symbol_references_exist() -> None:
    source = Path("securebox/ui/app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    checked: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute) or not isinstance(node.value, ast.Attribute):
            continue
        if not isinstance(node.value.value, ast.Name) or node.value.value.id != "ft":
            continue
        namespace = node.value.attr
        symbol = f"ft.{namespace}.{node.attr}"
        checked.append(symbol)
        assert hasattr(ft, namespace), f"Missing Flet namespace: ft.{namespace}"
        assert hasattr(getattr(ft, namespace), node.attr), f"Missing Flet symbol: {symbol}"

    assert checked


def test_auth_screen_renders_with_current_flet_api(tmp_path) -> None:
    page = FakePage()

    app = build_app(page, tmp_path / "securebox.sqlite3")

    assert isinstance(app, SecureBoxFletApp)
    assert page.controls
    assert page.updated == 1


def test_auth_screen_defaults_to_chinese_with_hidden_password(tmp_path) -> None:
    page = FakePage()
    app = build_app(page, tmp_path / "securebox.sqlite3")

    text_fields = find_controls(page, ft.TextField)
    labels = {field.label for field in text_fields}
    assert app.state.language == "zh"
    assert "主密码" in labels
    assert "确认主密码" in labels

    password_fields = [field for field in text_fields if field.label in {"主密码", "确认主密码"}]
    assert password_fields
    assert all(field.password is True for field in password_fields)
    assert all(field.can_reveal_password is False for field in password_fields)

    show_password = next(
        checkbox for checkbox in find_controls(page, ft.Checkbox) if checkbox.label == "显示密码"
    )
    assert show_password.value is False


def test_language_toggle_rerenders_english_labels(tmp_path) -> None:
    page = FakePage()
    app = build_app(page, tmp_path / "securebox.sqlite3")

    app._toggle_language()

    labels = {field.label for field in find_controls(page, ft.TextField)}
    assert app.state.language == "en"
    assert "Master password" in labels
    assert "Confirm master password" in labels


def test_wrong_master_password_opens_error_dialog(tmp_path) -> None:
    state = SecureBoxAppState.create(tmp_path / "securebox.sqlite3")
    state.auth_service.initialize("correct horse battery staple")
    page = FakePage()
    app = SecureBoxFletApp(page, state)

    app.render()

    password = next(
        field for field in find_controls(page, ft.TextField) if field.label == "主密码"
    )
    password.value = "wrong password"
    submit = next(button for button in find_controls(page, ft.FilledButton))
    submit.on_click(None)

    assert len(page.dialogs) == 1
    dialog_text = {text.value for text in find_controls(page, ft.Text)}
    assert "解锁失败" in dialog_text
    assert any("主密码不正确" in value for value in dialog_text)


def test_main_screen_renders_with_current_flet_api(tmp_path) -> None:
    state = SecureBoxAppState.create(tmp_path / "securebox.sqlite3")
    state.session = state.auth_service.initialize("correct horse battery staple")
    state.lock_service.unlock()
    page = FakePage()
    app = SecureBoxFletApp(page, state)

    app.render()

    assert page.controls
    assert page.updated == 1


def test_language_toggle_preserves_selected_main_tab(tmp_path) -> None:
    state = SecureBoxAppState.create(tmp_path / "securebox.sqlite3")
    state.session = state.auth_service.initialize("correct horse battery staple")
    state.lock_service.unlock()
    page = FakePage()
    app = SecureBoxFletApp(page, state)
    app.render()
    app._handle_tab_change(SimpleNamespace(data="2", control=SimpleNamespace(selected_index=2)))

    app._toggle_language()

    tabs = next(control for control in find_controls(page, ft.Tabs))
    assert app.state.language == "en"
    assert app.state.selected_tab_index == 2
    assert tabs.selected_index == 2


def test_mobile_main_screen_uses_compact_lock_button(tmp_path) -> None:
    state = SecureBoxAppState.create(tmp_path / "securebox.sqlite3")
    state.session = state.auth_service.initialize("correct horse battery staple")
    state.lock_service.unlock()
    page = FakePage(platform=ft.PagePlatform.ANDROID)
    app = SecureBoxFletApp(page, state)

    app.render()

    lock_buttons = [
        button for button in find_controls(page, ft.IconButton) if button.data == "lock"
    ]
    assert len(lock_buttons) == 1
    assert lock_buttons[0].tooltip == "锁定"


def test_vault_new_entry_uses_dialog_instead_of_persistent_form(tmp_path) -> None:
    state = SecureBoxAppState.create(tmp_path / "securebox.sqlite3")
    state.session = state.auth_service.initialize("correct horse battery staple")
    state.lock_service.unlock()
    page = FakePage()
    app = SecureBoxFletApp(page, state)

    app.render()

    page_field_labels = {field.label for field in find_controls(page, ft.TextField)}
    assert "标题" not in page_field_labels
    assert "用户名" not in page_field_labels

    new_buttons = [
        button for button in find_controls(page, ft.FilledButton) if button.data == "new-entry"
    ]
    assert len(new_buttons) == 1
    new_buttons[0].on_click(None)

    dialog_fields = {
        field.label: field for field in find_controls(page, ft.TextField) if field.data
    }
    assert {"标题", "用户名", "密码", "URL", "备注"} <= set(dialog_fields)
    dialog_fields["标题"].value = "Email"
    dialog_fields["用户名"].value = "alice"
    dialog_fields["密码"].value = "secret-password"
    save_button = next(
        button for button in find_controls(page, ft.FilledButton) if button.data == "save-entry"
    )
    save_button.on_click(None)

    entries = VaultService(state.connection, state.session.data_key).list_entries()
    assert len(entries) == 1
    assert entries[0].title == "Email"
    assert entries[0].username == "alice"


def test_vault_edit_entry_uses_prefilled_dialog(tmp_path) -> None:
    state = SecureBoxAppState.create(tmp_path / "securebox.sqlite3")
    state.session = state.auth_service.initialize("correct horse battery staple")
    state.lock_service.unlock()
    entry = VaultService(state.connection, state.session.data_key).create_entry(
        PasswordEntryDraft(
            title="Email",
            username="alice",
            password="secret-password",
            url="https://example.com",
        )
    )
    page = FakePage()
    app = SecureBoxFletApp(page, state)

    app.render()

    edit_button = next(
        button for button in find_controls(page, ft.IconButton) if button.data == "edit-entry"
    )
    edit_button.on_click(None)

    dialog_fields = {
        field.data: field for field in find_controls(page, ft.TextField) if field.data
    }
    assert dialog_fields["entry-title"].value == "Email"
    assert dialog_fields["entry-username"].value == "alice"

    dialog_fields["entry-username"].value = "bob"
    save_button = next(
        button for button in find_controls(page, ft.FilledButton) if button.data == "save-entry"
    )
    save_button.on_click(None)

    updated = VaultService(state.connection, state.session.data_key).get_entry(entry.id)
    assert updated.username == "bob"


def test_vault_copy_button_copies_password_not_url(tmp_path) -> None:
    state = SecureBoxAppState.create(tmp_path / "securebox.sqlite3")
    state.session = state.auth_service.initialize("correct horse battery staple")
    state.lock_service.unlock()
    VaultService(state.connection, state.session.data_key).create_entry(
        PasswordEntryDraft(
            title="Email",
            username="alice",
            password="secret-password",
            url="https://example.com",
        )
    )
    page = FakePage()
    app = SecureBoxFletApp(page, state)

    app.render()

    copy_buttons = [
        button for button in find_controls(page, ft.IconButton) if button.data == "copy-password"
    ]
    assert len(copy_buttons) == 1

    copy_buttons[0].on_click(None)

    assert page.clipboard == "secret-password"
    assert page.clipboard != "https://example.com"


def test_vault_copy_button_uses_modern_flet_clipboard_api(tmp_path) -> None:
    state = SecureBoxAppState.create(tmp_path / "securebox.sqlite3")
    state.session = state.auth_service.initialize("correct horse battery staple")
    state.lock_service.unlock()
    VaultService(state.connection, state.session.data_key).create_entry(
        PasswordEntryDraft(
            title="Email",
            username="alice",
            password="secret-password",
            url="https://example.com",
        )
    )
    page = FakeModernPage(platform=ft.PagePlatform.ANDROID)
    app = SecureBoxFletApp(page, state)

    app.render()

    copy_buttons = [
        button for button in find_controls(page, ft.IconButton) if button.data == "copy-password"
    ]
    assert len(copy_buttons) == 1

    copy_buttons[0].on_click(None)

    assert page.clipboard.values[-1] == "secret-password"
    assert page.clipboard.values[-1] != "https://example.com"
