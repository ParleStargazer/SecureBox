"""Clipboard auto-clear timing service."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

Clock = Callable[[], float]


@dataclass
class ClipboardAutoClearService:
    clear_after_seconds: float = 30.0
    clock: Clock = time.monotonic
    expires_at: float | None = None

    def mark_copied(self) -> None:
        self.expires_at = self.clock() + self.clear_after_seconds

    def should_clear(self) -> bool:
        return self.expires_at is not None and self.clock() >= self.expires_at

    def clear_if_expired(self, clear_clipboard: Callable[[], None]) -> bool:
        if not self.should_clear():
            return False
        clear_clipboard()
        self.expires_at = None
        return True

