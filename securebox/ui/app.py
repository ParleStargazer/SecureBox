"""Flet application shell."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import flet as ft


def build_home(page: ft.Page) -> None:
    """Build a minimal placeholder shell used before feature views are wired."""
    import flet as ft

    page.title = "SecureBox"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.add(
        ft.Column(
            [
                ft.Icon(ft.Icons.LOCK_SHIELD, size=54, color=ft.Colors.BLUE_700),
                ft.Text("SecureBox", size=28, weight=ft.FontWeight.BOLD),
                ft.Text("Local password manager", size=14, color=ft.Colors.GREY_700),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        )
    )


def run_app() -> None:
    """Run the local Flet desktop application.

    SecureBox intentionally does not expose a Web server entry point.
    """
    import flet as ft

    ft.app(target=build_home)
