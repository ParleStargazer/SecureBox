import ast
from pathlib import Path
from types import SimpleNamespace

import flet as ft

from securebox.config import DEFAULT_DB_NAME, get_default_data_dir
from securebox.ui.app import SecureBoxAppState, SecureBoxFletApp, build_app
from securebox.ui.theme import apply_theme


class FakePage:
    def __init__(self, platform=None) -> None:
        self.controls = []
        self.platform = platform
        self.window = SimpleNamespace()
        self.updated = 0

    def add(self, *controls) -> None:
        self.controls.extend(controls)

    def update(self) -> None:
        self.updated += 1

    def set_clipboard(self, value: str) -> None:
        self.clipboard = value


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


def test_main_screen_renders_with_current_flet_api(tmp_path) -> None:
    state = SecureBoxAppState.create(tmp_path / "securebox.sqlite3")
    state.session = state.auth_service.initialize("correct horse battery staple")
    state.lock_service.unlock()
    page = FakePage()
    app = SecureBoxFletApp(page, state)

    app.render()

    assert page.controls
    assert page.updated == 1
