"""Login retry delay service."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetryDelayService:
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    failures: int = 0

    def record_failure(self) -> float:
        self.failures += 1
        return self.current_delay()

    def record_success(self) -> None:
        self.failures = 0

    def current_delay(self) -> float:
        if self.failures <= 0:
            return 0.0
        delay = self.base_delay_seconds * (2 ** (self.failures - 1))
        return min(delay, self.max_delay_seconds)

