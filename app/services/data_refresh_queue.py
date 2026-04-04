from __future__ import annotations

from datetime import datetime, timedelta, timezone
import threading
from typing import Callable


class DataRefreshQueue:
    def __init__(self, cooldown: timedelta | None = None) -> None:
        self._cooldown = cooldown or timedelta(minutes=5)
        self._state: dict[str, datetime] = {}
        self._lock = threading.RLock()

    def should_enqueue(self, symbol: str, now_utc: datetime | None = None) -> bool:
        now_utc = now_utc or datetime.now(timezone.utc)
        with self._lock:
            last = self._state.get(symbol)
            if last and (now_utc - last) < self._cooldown:
                return False
            self._state[symbol] = now_utc
            return True

    def enqueue_stock_sync(self, background_tasks, symbol: str, refresh_fn: Callable) -> bool:
        if not self.should_enqueue(symbol):
            return False
        background_tasks.add_task(refresh_fn, [symbol], "sync")
        return True

    def clear(self) -> None:
        with self._lock:
            self._state.clear()


_queue_singleton: DataRefreshQueue | None = None
_queue_singleton_lock = threading.RLock()


def get_data_refresh_queue() -> DataRefreshQueue:
    global _queue_singleton
    with _queue_singleton_lock:
        if _queue_singleton is None:
            _queue_singleton = DataRefreshQueue()
        return _queue_singleton
