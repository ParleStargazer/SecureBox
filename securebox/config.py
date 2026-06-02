"""Project-wide configuration constants."""

import os
from pathlib import Path

APP_NAME = "SecureBox"
CRYPTO_VERSION = 1
DEFAULT_DB_NAME = "securebox.sqlite3"


def get_default_data_dir() -> Path:
    app_storage_dir = os.getenv("FLET_APP_STORAGE_DATA")
    platform = os.getenv("FLET_PLATFORM", "").lower()
    if app_storage_dir and platform in {"android", "ios"}:
        return Path(app_storage_dir)
    try:
        return Path.home() / ".securebox"
    except RuntimeError:
        if app_storage_dir:
            return Path(app_storage_dir)
        return Path.cwd() / ".securebox"


DEFAULT_DATA_DIR = get_default_data_dir()
