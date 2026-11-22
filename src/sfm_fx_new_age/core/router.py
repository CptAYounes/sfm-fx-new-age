from __future__ import annotations

from collections import OrderedDict, defaultdict, deque
from collections.abc import Callable
import heapq
from itertools import count
from threading import RLock, get_ident
from time import monotonic

from sfm_fx_new_age.contracts.models import Event

EventHandler = Callable[[Event], None]


class BackpressureError(RuntimeError):
    """Capacity exhausted; producer must pause/reconcile, never silently drop data."""


class PriorityEventRouter:
    """Bounded priority queues; callbacks drain on the owning core thread, never Qt workers."""

    def __init__(self, capacity_per_priority: int = 4096, lkv_capacity: int = 4096, *, owner_thread: int | None = None) -> None:
        if capacity_per_priority < 1 or lkv_capacity < 1:
            raise ValueError('Positive queue/LKV capacity required')
        self._listeners: dict[str, list[EventHandler]] = defaultdict(list)
        self._queue: list[tuple[int, int, Event]] = []
        self._sequence = count()
        self._last_known: OrderedDict[tuple[str, str], Event] = OrderedDict()
        self._counts = [0, 0, 0, 0]
        self._lock = RLock()
        self._drain_lock = RLock()
        self._draining = False
        self.capacity_per_priority = capacity_per_priority
        self.lkv_capacity = lkv_capacity
        self.errors: deque[dict[str, str]] = deque(maxlen=100)
        self.owner_thread = owner_thread
        self._published = defaultdict(int)
        self._delivered = defaultdict(int)
        self._queued_at = {}
        self.max_latency_seconds = 0.0

    def subscribe(self, topic: str, handler: EventHandler) -> Callable[[], None]:
        with self._lock:
            if handler not in self._listeners[topic]:
                self._listeners[topic].append(handler)
        def unsubscribe() -> None:
            with self._lock:
                if handler in self._listeners[topic]:
                    self._listeners[topic].remove(handler)
        return unsubscribe

    def publish(self, event: Event) -> None:
        with self._lock:
            priority = int(event.priority)
            if priority not in range(4):
                raise ValueError('P0-P3 priority required')
            if self._counts[priority] >= self.capacity_per_priority:
                raise BackpressureError(f'P{priority} queue full; pause producer, no event accepted')
            heapq.heappush(self._queue, (priority, next(self._sequence), event))
            self._counts[priority] += 1
            self._published[event.topic] += 1
            self._queued_at[event.event_id] = monotonic()

    def drain(self, limit: int | None = None) -> int:
        if self.owner_thread is not None and get_ident() != self.owner_thread:
            raise RuntimeError('Only the owning core thread may drain callbacks')
        with self._drain_lock:
            if self._draining:
                return 0
            self._draining = True
            delivered = 0
            try:
                while limit is None or delivered < limit:
                    with self._lock:
                        if not self._queue:
                            break
                        priority, _, event = heapq.heappop(self._queue)
                        self._counts[priority] -= 1
                        self._delivered[event.topic] += 1
                        queued_at = self._queued_at.pop(event.event_id, monotonic())
                        self.max_latency_seconds = max(self.max_latency_seconds, monotonic() - queued_at)
                        handlers = tuple(self._listeners.get(event.topic, ())) + tuple(self._listeners.get('*', ()))
                        key = (event.topic, event.partition_key)
                        self._last_known[key] = event
                        self._last_known.move_to_end(key)
                        if len(self._last_known) > self.lkv_capacity:
                            self._last_known.popitem(last=False)
                    for handler in handlers:
                        try:
                            handler(event)
                        except Exception as exc:
                            self.errors.append({'event_id': event.event_id, 'topic': event.topic,
                                                'error_type': type(exc).__name__})
                    delivered += 1
            finally:
                self._draining = False
            return delivered

    def last_known(self, topic: str, partition_key: str = 'GLOBAL') -> Event | None:
        with self._lock:
            return self._last_known.get((topic, partition_key))

    @property
    def queued_count(self) -> int:
        with self._lock:
            return len(self._queue)

    def metrics(self) -> dict[str, object]:
        with self._lock:
            return {'queued': len(self._queue), 'by_priority': list(self._counts),
                    'subscriber_count': sum(len(v) for v in self._listeners.values()),
                    'callback_errors': len(self.errors), 'last_known_entries': len(self._last_known),
                    'published_by_topic': dict(self._published), 'delivered_by_topic': dict(self._delivered),
                    'max_latency_seconds': self.max_latency_seconds}
