from datetime import datetime, timedelta, timezone

from app.services.data_refresh_queue import DataRefreshQueue


class _BackgroundTasksStub:
    def __init__(self):
        self.calls = []

    def add_task(self, fn, *args):
        self.calls.append((fn, args))


def _fake_refresh(*args):
    return args


def test_should_enqueue_blocks_within_cooldown():
    queue = DataRefreshQueue(cooldown=timedelta(minutes=5))
    now = datetime.now(timezone.utc)
    assert queue.should_enqueue("AAPL", now) is True
    assert queue.should_enqueue("AAPL", now + timedelta(minutes=1)) is False


def test_enqueue_stock_sync_adds_background_task_once_per_cooldown_window():
    queue = DataRefreshQueue(cooldown=timedelta(minutes=5))
    bt = _BackgroundTasksStub()
    assert queue.enqueue_stock_sync(bt, "AAPL", _fake_refresh) is True
    assert queue.enqueue_stock_sync(bt, "AAPL", _fake_refresh) is False
    assert len(bt.calls) == 1
    assert bt.calls[0][1] == (["AAPL"], "sync")
