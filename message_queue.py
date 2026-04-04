"""
This module provides `BasicMessageQueue`, a thin, documented wrapper
around `queue.Queue` that the UI and kitchen use to exchange messages.

Design notes:
- Messages are simple dictionaries with keys `sender` and `body`.
- `send()` uses a non-blocking `put(..., block=False)` so callers can
  detect `queue.Full` and react (e.g., show a warning in the UI).
- `peek()` intentionally reads the underlying deque for UI previewing
  but wraps the access in a lock and exception handling.
"""

import queue
import threading
from typing import Any, Dict, Optional


class BasicMessageQueue:
    """A thread-safe FIFO queue wrapper used across the app.

    Example message: {"sender": "Table 3", "body": <Order>}
    """

    def __init__(self, name: str, maxsize: int = 0):
        self.name = name
        self._queue = queue.Queue(maxsize=maxsize)
        self._lock = threading.Lock()

    def send(self, sender: str, body: Any) -> None:
        """Enqueue a message in a non-blocking way.

        Raises `queue.Full` if the queue is at capacity so the caller
        (usually the UI) can display a backpressure warning.
        """
        try:
            self._queue.put({"sender": sender, "body": body}, block=False)
            print(f"  [SEND] '{self.name}' got order: '{body}' from {sender}")
        except queue.Full:
            print(f"  [SEND] '{self.name}' is full; cannot accept order from {sender}")
            raise

    def receive(self, timeout: float = 3.0) -> Optional[Dict]:
        """Remove and return the next message or None on timeout.

        `timeout` is in seconds; callers should handle `None` when the
        queue is empty.
        """
        try:
            msg = self._queue.get(timeout=timeout)
            print(f"  [RECEIVE] '{self.name}' processing order: '{msg['body']}' from {msg['sender']}")
            return msg
        except queue.Empty:
            print(f"  [RECEIVE] '{self.name}' no orders to process (queue is empty)")
            return None

    def peek(self) -> Optional[Dict]:
        """Return the next message without removing it from the queue.

        NOTE: accessing `self._queue.queue` reads the internal deque used by
        `queue.Queue`. This is acceptable for UI preview but must be done
        while holding a lock and wrapped in exception handling.
        """
        with self._lock:
            try:
                msg = self._queue.queue[0]
                body = msg.get('body') if isinstance(msg, dict) else msg
                sender = msg.get('sender') if isinstance(msg, dict) else None
                display = body.description if hasattr(body, 'description') else body
                print(f"  [PEEK] '{self.name}' next: {display} (from {sender})")
                return msg
            except IndexError:
                # queue is empty
                print(f"  [PEEK] '{self.name}' is empty")
                return None
            except Exception as exc:
                # Unexpected errors should not crash the application.
                print(f"  [PEEK] '{self.name}' peek error: {exc}")
                return None

    def size(self) -> int:
        """Return current queue size."""
        return self._queue.qsize()

    def is_empty(self) -> bool:
        """Return True when queue is empty (and log the check)."""
        is_empty = self._queue.empty()
        print(f"  [EMPTY?] '{self.name}' is empty: {is_empty}")
        return is_empty
