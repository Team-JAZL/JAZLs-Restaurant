"""
This module is UI-only: it builds the Tkinter widgets and wires them to the
message queue and kitchen worker. Business logic and queue behavior live in
their respective modules (`order.py`, `message_queue.py`, `kitchen.py`).

Enhancements:
- Numeric keypad for table input
- Interactive dish buttons in a grid
- A "Current Order" cart allowing multiple dishes to be batched
  and submitted together.
"""

import tkinter as tk
from tkinter import messagebox, ttk
import queue
from typing import List, Optional

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

        # UI state
        self.cart: List[str] = []  # temporary cart for current table
        self.table_buffer: str = ""  # digits entered via keypad
        self.selected_table: Optional[str] = None  # confirmed table number

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
        """Build the left-side customer/order UI with keypad, menu, and cart."""
        frame = ttk.LabelFrame(self.root, text="Place Order (Customer App)")
        frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Table display (shows entered digits)
        ttk.Label(frame, text="Table Number:").grid(row=0, column=0, columnspan=3, pady=2)
        self.table_var = tk.StringVar(value="")
        self.table_display = ttk.Label(frame, textvariable=self.table_var, relief="sunken", width=18, anchor="center")
        self.table_display.grid(row=1, column=0, columnspan=3, pady=5)

        # Numeric keypad (3x4)
        keypad_frame = ttk.Frame(frame)
        keypad_frame.grid(row=2, column=0, columnspan=3, pady=5)

        keys = [
            ("1", 0, 0), ("2", 0, 1), ("3", 0, 2),
            ("4", 1, 0), ("5", 1, 1), ("6", 1, 2),
            ("7", 2, 0), ("8", 2, 1), ("9", 2, 2),
            ("Clear", 3, 0), ("0", 3, 1), ("Enter", 3, 2),
        ]

        for (label, r, c) in keys:
            btn = ttk.Button(keypad_frame, text=label, command=lambda t=label: self._on_keypad(t))
            btn.grid(row=r, column=c, ipadx=10, ipady=8, padx=3, pady=3, sticky="nsew")

        for i in range(3):
            keypad_frame.grid_columnconfigure(i, weight=1)

        # Menu (grid of dish buttons)
        ttk.Label(frame, text="Menu:").grid(row=3, column=0, columnspan=3, pady=(10, 2))
        menu_frame = ttk.Frame(frame)
        menu_frame.grid(row=4, column=0, columnspan=3)

        self.menu_items = [
            "Pepperoni Pizza",
            "Hawaiian Deluxe",
            "All-Meat Pizza",
            "Triple Cheese Pizza",
            "Ham & Cheese Pizza",
            "Veggie Burger",
            "Caesar Salad",
            "Pasta Carbonara",
        ]

        # Create dish buttons in a 2-column grid for easy tapping
        for idx, dish in enumerate(self.menu_items):
            r = idx // 2
            c = idx % 2
            b = ttk.Button(menu_frame, text=dish, command=lambda d=dish: self._on_dish_click(d))
            b.grid(row=r, column=c, padx=4, pady=4, sticky="nsew", ipadx=6, ipady=8)

        for j in range(2):
            menu_frame.grid_columnconfigure(j, weight=1)

        # Cart (current order) listbox
        ttk.Label(frame, text="Current Order (Cart):").grid(row=5, column=0, columnspan=3, pady=(10, 2))
        self.cart_listbox = tk.Listbox(frame, width=30, height=6)
        self.cart_listbox.grid(row=6, column=0, columnspan=3, pady=(0, 5))

        # Cart actions: submit, clear, remove selected
        cart_btn_frame = ttk.Frame(frame)
        cart_btn_frame.grid(row=7, column=0, columnspan=3, pady=6)
        ttk.Button(cart_btn_frame, text="Submit Order", command=self.submit_cart).pack(side="left", padx=6)
        ttk.Button(cart_btn_frame, text="Clear Cart", command=self.clear_cart).pack(side="left", padx=6)
        ttk.Button(cart_btn_frame, text="Remove Selected", command=self.remove_selected_cart_item).pack(side="left", padx=6)

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

    # -------------------- Cart & Keypad Handlers --------------------
    def _on_keypad(self, key: str) -> None:
        """Handle keypad presses: digits, Clear, and Enter."""
        if key == "Clear":
            self.table_buffer = ""
            self.selected_table = None
            self.table_var.set("")
        elif key == "Enter":
            if not self.table_buffer:
                messagebox.showwarning("Input Error", "Please enter a table number first.")
                return
            # Confirm the table number
            self.selected_table = self.table_buffer
            messagebox.showinfo("Table Selected", f"Table {self.selected_table} selected")
        else:
            # Append digit
            if len(self.table_buffer) < 4:  # limit length for sanity
                self.table_buffer += key
                self.table_var.set(self.table_buffer)

    def _on_dish_click(self, dish: str) -> None:
        """Add the tapped dish to the temporary cart list."""
        self.cart.append(dish)
        self._update_cart_listbox()

    def _update_cart_listbox(self) -> None:
        """Refresh the cart listbox to reflect `self.cart`."""
        self.cart_listbox.delete(0, tk.END)
        for item in self.cart:
            self.cart_listbox.insert(tk.END, item)

    def remove_selected_cart_item(self) -> None:
        """Remove the selected item from the cart listbox and state."""
        sel = self.cart_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        try:
            del self.cart[idx]
        except IndexError:
            return
        self._update_cart_listbox()

    def clear_cart(self) -> None:
        """Clear the current cart contents."""
        self.cart.clear()
        self._update_cart_listbox()

    def submit_cart(self) -> None:
        """Attempt to submit all cart items as separate `Order`s to the queue.

        Handles `queue.Full` by preserving unsent items in the cart and
        warning the user if the kitchen is overwhelmed.
        """
        # Determine table number: prefer confirmed selection, fall back to buffer
        table = self.selected_table or self.table_buffer
        if not table:
            messagebox.showwarning("Input Error", "Please set a table number using the keypad (press Enter).")
            return

        if not self.cart:
            messagebox.showwarning("Cart Empty", "No dishes selected. Tap dishes to add them to the cart.")
            return

        remaining: List[str] = []
        sent_count = 0
        for idx, dish in enumerate(self.cart):
            order = Order(dish=dish, table_number=table)
            try:
                self.queue.send(sender=order.sender, body=order)
                # Add to pending listbox so UI shows the order is queued
                self.kitchen_list.insert(tk.END, order.description)
                sent_count += 1
            except queue.Full:
                # Kitchen can't accept more; preserve remaining items
                remaining = self.cart[idx:]
                messagebox.showwarning("Kitchen Full", "Kitchen is overwhelmed. Some items remain in your cart.")
                break

        # Update cart state to whatever couldn't be sent
        self.cart = remaining
        self._update_cart_listbox()

        # If everything sent, optionally clear the table buffer/selection
        if not self.cart and sent_count > 0:
            # clear table so next order requires explicit entry
            self.table_buffer = ""
            self.selected_table = None
            self.table_var.set("")

    # -------------------- Existing helpers (status / callbacks) --------------------
    def place_order(self) -> None:
        # Legacy single-order path retained for compatibility (not used by new UI)
        table = self.table_buffer.strip() or (self.selected_table or "")
        if not table:
            messagebox.showwarning("Input Error", "Please enter Table and Dish!")
            return

        # If dish is present in a combobox (legacy) handle it; otherwise the
        # modern UI uses cart/submit_cart instead.
        try:
            dish = self.dish_var.get()
        except Exception:
            dish = None

        if not dish:
            messagebox.showwarning("Input Error", "Please select a dish or use the cart.")
            return

        order = Order(dish=dish, table_number=table)
        try:
            self.queue.send(sender=order.sender, body=order)
        except queue.Full:
            messagebox.showwarning("Kitchen Full", "Kitchen is overwhelmed. Please wait before sending more orders.")
            return

        self.kitchen_list.insert(tk.END, order.description)
        # reset table buffer/selection after single-send
        self.table_buffer = ""
        self.selected_table = None
        self.table_var.set("")

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
