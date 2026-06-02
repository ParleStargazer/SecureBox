"""Flet theme helpers."""

from __future__ import annotations

import flet as ft


def apply_theme(page: ft.Page) -> None:
    page.title = "SecureBox"
    platform = getattr(page, "platform", None)
    if platform is None or platform.is_desktop():
        page.window.width = 1060
        page.window.height = 760
    page.padding = 24
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.BLUE,
        visual_density=ft.VisualDensity.COMFORTABLE,
    )
