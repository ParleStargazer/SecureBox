import ast
from pathlib import Path

import flet as ft

from securebox.ui.app import SecureBoxAppState


def test_app_state_initializes_local_database(tmp_path) -> None:
    db_path = tmp_path / "securebox.sqlite3"

    state = SecureBoxAppState.create(db_path)

    assert state.db_path == db_path
    assert state.auth_service.is_initialized() is False


def test_flet_symbol_references_exist() -> None:
    source = Path("securebox/ui/app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    checked: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute) or not isinstance(node.value, ast.Attribute):
            continue
        if not isinstance(node.value.value, ast.Name) or node.value.value.id != "ft":
            continue
        if node.value.attr == "Icons":
            checked.append(f"ft.Icons.{node.attr}")
            assert hasattr(ft.Icons, node.attr), f"Missing Flet icon: {node.attr}"
        elif node.value.attr == "Colors":
            checked.append(f"ft.Colors.{node.attr}")
            assert hasattr(ft.Colors, node.attr), f"Missing Flet color: {node.attr}"

    assert checked
