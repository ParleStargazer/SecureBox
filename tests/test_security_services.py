from securebox.services.clipboard_service import ClipboardAutoClearService
from securebox.services.lock_service import IdleLockService
from securebox.services.retry_delay_service import RetryDelayService


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_idle_lock_service_locks_after_timeout() -> None:
    clock = FakeClock()
    service = IdleLockService(timeout_seconds=5, clock=clock)

    service.unlock()
    clock.advance(4)
    assert service.lock_if_idle() is False

    clock.advance(1)
    assert service.lock_if_idle() is True
    assert service.locked is True


def test_idle_lock_service_activity_resets_timeout() -> None:
    clock = FakeClock()
    service = IdleLockService(timeout_seconds=5, clock=clock)

    service.unlock()
    clock.advance(4)
    service.mark_activity()
    clock.advance(4)

    assert service.lock_if_idle() is False


def test_clipboard_auto_clear_runs_callback_after_expiry() -> None:
    clock = FakeClock()
    service = ClipboardAutoClearService(clear_after_seconds=30, clock=clock)
    cleared = []

    service.mark_copied()
    clock.advance(29)
    assert service.clear_if_expired(lambda: cleared.append(True)) is False

    clock.advance(1)
    assert service.clear_if_expired(lambda: cleared.append(True)) is True
    assert cleared == [True]
    assert service.expires_at is None


def test_retry_delay_increases_and_resets() -> None:
    service = RetryDelayService(base_delay_seconds=1, max_delay_seconds=5)

    assert service.record_failure() == 1
    assert service.record_failure() == 2
    assert service.record_failure() == 4
    assert service.record_failure() == 5

    service.record_success()
    assert service.current_delay() == 0

