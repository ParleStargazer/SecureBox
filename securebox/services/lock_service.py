"""Idle auto-lock service."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

Clock = Callable[[], float]


@dataclass
class IdleLockService:
    timeout_seconds: float = 300.0
    clock: Clock = time.monotonic
    locked: bool = True
    last_activity_at: float | None = None

    def unlock(self) -> None:
        self.locked = False
        self.mark_activity()

    def lock(self) -> None:
        self.locked = True

    def mark_activity(self) -> None:
        self.last_activity_at = self.clock()

    def should_lock(self) -> bool:
        if self.locked or self.last_activity_at is None:
            return False
        return self.clock() - self.last_activity_at >= self.timeout_seconds

    def lock_if_idle(self) -> bool:
        if self.should_lock():
            self.lock()
            return True
        return False

