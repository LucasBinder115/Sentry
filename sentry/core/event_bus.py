import threading
from typing import Callable, Dict, List, Any


class EventBus:
    def __init__(self):
        self._lock = threading.RLock()
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}

    def subscribe(self, event_name: str, handler: Callable[[Dict[str, Any]], None]):
        with self._lock:
            self._subscribers.setdefault(event_name, []).append(handler)

    def unsubscribe(self, event_name: str, handler: Callable[[Dict[str, Any]], None]):
        with self._lock:
            handlers = self._subscribers.get(event_name, [])
            if handler in handlers:
                handlers.remove(handler)

    def publish(self, event_name: str, payload: Dict[str, Any] | None = None):
        payload = payload or {}
        with self._lock:
            handlers = list(self._subscribers.get(event_name, []))
        for h in handlers:
            try:
                h(payload)
            except Exception:
                pass


_bus = EventBus()


def get_event_bus() -> EventBus:
    return _bus
