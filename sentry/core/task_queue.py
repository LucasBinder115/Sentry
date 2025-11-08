from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Any
import threading


class TaskQueue:
    def __init__(self, max_workers: int = 4):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="sentry-worker")
        self._lock = threading.RLock()
        self._shutdown = False

    def submit(self, fn: Callable[..., Any], *args, **kwargs) -> Future:
        with self._lock:
            if self._shutdown:
                raise RuntimeError("TaskQueue is shut down")
            return self._executor.submit(fn, *args, **kwargs)

    def shutdown(self, wait: bool = False):
        with self._lock:
            self._shutdown = True
            self._executor.shutdown(wait=wait, cancel_futures=True)


_queue = TaskQueue()


def get_task_queue() -> TaskQueue:
    return _queue
