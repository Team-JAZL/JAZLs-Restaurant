"""
This module runs the kitchen worker loop that processes `Order` objects
delivered via `BasicMessageQueue`.

The KitchenWorker runs in a dedicated thread and uses callbacks to report
status and completed orders back to the UI layer. The callbacks are invoked
from the worker thread; the UI should schedule them on the main thread
using a thread-safe mechanism (e.g., `root.after`).
"""

import threading
import time
from typing import Callable, Optional

from message_queue import BasicMessageQueue
from order import Order


class KitchenWorker:
    """Background kitchen processor.

    The worker pulls messages from the provided `order_queue`. Each message's
    `body` is expected to be an `Order` instance. Two optional callbacks can be
    provided:
      - status_callback(str): called to report a textual kitchen status
      - order_done_callback(Order): called when an order is finished
    """

    def __init__(
        self,
        order_queue: BasicMessageQueue,
        processing_delay: float = 10.0,
        status_callback: Optional[Callable[[str], None]] = None,
        order_started_callback: Optional[Callable[[Order], None]] = None,
        order_done_callback: Optional[Callable[[Order], None]] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
    ):
        self.order_queue = order_queue
        self.processing_delay = processing_delay
        self.status_callback = status_callback
        self.order_started_callback = order_started_callback
        self.order_done_callback = order_done_callback
        self.progress_callback = progress_callback
        self.running = False
        self.shutdown_event = threading.Event()
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the worker thread."""
        self.running = True
        self.shutdown_event.clear()
        self.thread = threading.Thread(target=self._run)
        self.thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the worker to stop and join the thread with a timeout."""
        self.running = False
        self.shutdown_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=timeout)

    def _run(self) -> None:
        """Worker main loop. Pulls messages and processes them."""
        while self.running and not self.shutdown_event.is_set():
            order_message = self.order_queue.receive(timeout=1.0)
            if order_message:
                body = order_message.get("body")
                # Ensure the message body is an Order instance; otherwise ignore.
                if not isinstance(body, Order):
                    continue

                # Notify observers that the kitchen is busy and a new order is starting
                self._notify_order_started(body)
                self._notify_status(f"🍕 Cooking {body.dish}…")
                self._notify_progress(0.0)

                # Simulate the cooking time in smaller increments and report progress
                total_seconds = max(self.processing_delay, 0.5)
                step = 0.25
                elapsed = 0.0
                while self.running and elapsed < total_seconds and not self.shutdown_event.is_set():
                    time.sleep(step)
                    elapsed += step
                    progress = min(1.0, elapsed / total_seconds)
                    self._notify_progress(progress)

                self._notify_progress(1.0)

                # Notify that the order is done
                self._notify_order_done(body)
            else:
                # No orders; report idle state
                self._notify_status("🌿 Idle")
                self._notify_progress(0.0)

    def _notify_status(self, status: str) -> None:
        """Invoke the status callback if provided."""
        if callable(self.status_callback):
            try:
                self.status_callback(status)
            except Exception:
                # Callbacks should not crash the worker
                pass

    def _notify_order_started(self, order: Order) -> None:
        """Invoke the order-started callback if provided."""
        if callable(self.order_started_callback):
            try:
                self.order_started_callback(order)
            except Exception:
                pass

    def _notify_order_done(self, order: Order) -> None:
        """Invoke the order-done callback if provided."""
        if callable(self.order_done_callback):
            try:
                self.order_done_callback(order)
            except Exception:
                pass

    def _notify_progress(self, progress: float) -> None:
        """Invoke the progress callback with a float between 0.0 and 1.0."""
        if callable(self.progress_callback):
            try:
                self.progress_callback(progress)
            except Exception:
                pass
