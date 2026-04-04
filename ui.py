"""
This module is UI-only: it builds the Tkinter widgets and wires them to the
message queue and kitchen worker. Business logic and queue behavior live in
their respective modules (`order.py`, `message_queue.py`, `kitchen.py`).
"""

import tkinter as tk
from tkinter import messagebox, ttk
import queue

from order import Order
from message_queue import BasicMessageQueue
from kitchen import KitchenWorker


class RestaurantOrderApp:
    """Tkinter application coordinating UI, queue, and kitchen worker.

    The UI constructs the widgets and forwards `Order` objects into the
    `BasicMessageQueue`. `KitchenWorker` runs in a separate thread and uses
    callbacks to notify the UI of status changes and completed orders.
    """

    QUEUE_MAX_SIZE = 10

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("JAZL's Pizzeria: Order System")

        # Message queue used to communicate with the kitchen worker
        self.queue = BasicMessageQueue("KitchenOrders", maxsize=self.QUEUE_MAX_SIZE)
        # Kitchen worker processes Order instances from the queue
        self.kitchen_worker = KitchenWorker(
            order_queue=self.queue,
            processing_delay=10.0,
            status_callback=self._schedule_status_update,
            order_done_callback=self._schedule_order_done,
        )

        # Build UI
        self.setup_customer_ui()
        self.setup_kitchen_ui()
        self.setup_queue_status_ui()

        # Start worker and bind close handler
        self.running = True
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.kitchen_worker.start()
        self.update_queue_depth()

    def setup_customer_ui(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Place Order (Customer App)")
        frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        ttk.Label(frame, text="Table Number:").pack(pady=2)
        self.table_entry = ttk.Entry(frame)
        self.table_entry.pack(pady=5)

        ttk.Label(frame, text="Select Dish:").pack(pady=2)
        self.dish_var = tk.StringVar()
        self.dish_box = ttk.Combobox(frame, textvariable=self.dish_var)
        self.dish_box["values"] = (
            "Pepperoni Pizza",
            "Hawaiian Deluxe",
            "All-Meat Pizza",
            "Triple Cheese Pizza",
            "Ham & Cheese Pizza",
            "Veggie Burger",
            "Caesar Salad",
            "Pasta Carbonara",
        )
        self.dish_box.pack(pady=5)

        ttk.Button(frame, text="Send to Kitchen", command=self.place_order).pack(pady=10)

    def setup_kitchen_ui(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Kitchen Monitor")
        frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        ttk.Label(frame, text="Pending Orders:").pack(anchor="w", padx=5)
        self.kitchen_list = tk.Listbox(frame, width=40, height=8)
        self.kitchen_list.pack(padx=5, pady=(0, 8))

        ttk.Label(frame, text="Processed Orders:").pack(anchor="w", padx=5)
        self.processed_list = tk.Listbox(frame, width=40, height=8)
        self.processed_list.pack(padx=5, pady=(0, 5))

        ttk.Button(frame, text="See Next Order", command=self.peek_order).pack(pady=(5, 2))
        self.peek_var = tk.StringVar(value="Next up: —")
        ttk.Label(frame, textvariable=self.peek_var, foreground="blue").pack(pady=(0, 5))

    def setup_queue_status_ui(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Queue Status")
        frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

        self.depth_var = tk.StringVar(value="Queue depth: 0")
        self.status_var = tk.StringVar(value="Kitchen: idle")

        ttk.Label(frame, textvariable=self.depth_var, font=("TkDefaultFont", 11, "bold")).pack(
            side="left", padx=20, pady=6
        )
        ttk.Label(frame, textvariable=self.status_var).pack(side="left", padx=20, pady=6)

    def place_order(self) -> None:
        """Create an Order and send it to the queue.

        Uses `queue.Full` handling to alert the user when the kitchen is at
        capacity.
        """
        table = self.table_entry.get().strip()
        dish = self.dish_var.get()

        if not table or not dish:
            messagebox.showwarning("Input Error", "Please enter Table and Dish!")
            return

        order = Order(dish=dish, table_number=table)
        try:
            # Body is the Order instance; kitchen expects Order objects
            self.queue.send(sender=order.sender, body=order)
        except queue.Full:
            messagebox.showwarning(
                "Kitchen Full",
                "Kitchen is overwhelmed. Please wait before sending more orders.",
            )
            return

        # Add pending entry to the listbox using the human-friendly description
        self.kitchen_list.insert(tk.END, order.description)
        self.table_entry.delete(0, tk.END)

    def peek_order(self) -> None:
        """Show a preview of the next queued order without dequeuing it."""
        msg = self.queue.peek()
        if not msg:
            self.peek_var.set("Queue is empty.")
            return

        body = msg.get("body") if isinstance(msg, dict) else msg
        if isinstance(body, Order):
            self.peek_var.set(f"Next up: {body.description}")
        else:
            self.peek_var.set(f"Next up: {body} — {msg.get('sender')}")

    def _schedule_status_update(self, status: str) -> None:
        """Schedule a status update on the UI thread."""
        self._safe_after(0, lambda: self.status_var.set(status))

    def _schedule_order_done(self, order: Order) -> None:
        """Schedule the UI update to mark an order done."""
        self._safe_after(0, lambda: self._mark_order_done(order))

    def _mark_order_done(self, order: Order) -> None:
        """Remove the pending entry matching the order id and append to processed."""
        for i in range(self.kitchen_list.size()):
            if f"[#{order.order_id}]" in self.kitchen_list.get(i):
                self.kitchen_list.delete(i)
                break

        self.processed_list.insert(tk.END, order.description)
        self.processed_list.see(tk.END)

    def _safe_after(self, delay: int, callback, *args, **kwargs) -> None:
        """Schedule a Tk callback only if the UI root still exists.

        This prevents scheduling callbacks after the window has started to
        shutdown which can raise `RuntimeError: main thread is not in main loop`.
        """
        if self.running and self.root.winfo_exists():
            try:
                self.root.after(delay, callback, *args, **kwargs)
            except RuntimeError:
                # Ignore attempts to schedule as the UI shuts down
                pass

    def on_close(self) -> None:
        """Gracefully stop the kitchen worker and exit the application."""
        self.running = False
        self.kitchen_worker.stop(timeout=5.0)
        self.root.destroy()

    def update_queue_depth(self) -> None:
        """Periodic update of the queue depth display."""
        self.depth_var.set(f"Queue depth: {self.queue.size()}")
        self.root.after(500, self.update_queue_depth)
