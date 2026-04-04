import tkinter as tk
from tkinter import messagebox, ttk
import threading
import queue
import time
from typing import Any, Dict, Optional

""" GROUP 1: JAZL
    Members: Cabales, Lean Vince A.
             Calix, Zuriel Eliazar D.
             Escrupulo, Ma. Asherah Francine Faith S.
             Porras, Jessie Loraine P. 
             
    Topic: Basic Message Queue
    Description: This code demonstrates a simple implementation of a basic message queue using
                 a restaurant order system analogy that receives orders in a FIFO basis.

"""

class BasicMessageQueue:

    def __init__(self, name: str, maxsize: int = 0):
        self.name   = name
        self._queue = queue.Queue(maxsize=maxsize)
        self._lock  = threading.Lock()

    # sends order to kitchen ( produces a message into the queue)
    def send(self, sender: str, body: Any) -> None:
        """Producer sends a message. Non-blocking."""
        self._queue.put({"sender": sender, "body": body})
        print(f"  [SEND] '{self.name}' got order: '{body}' from {sender}")

    # kitchen worker thread calls receive to get next order (consumes a message from the queue)
    def receive(self, timeout: float = 3.0) -> Optional[Dict]:
        """Consumer extracts (destructive) the next message. Blocking."""
        try:
            msg =  self._queue.get(timeout=timeout)
            print(f"  [RECEIVE] '{self.name}' processing order: '{msg['body']}' from {msg['sender']}")
            return msg
        except queue.Empty:
            print(f"  [RECEIVE] '{self.name}' no orders to process (queue is empty)")
            return None
        
    # shows next order without removing it from the queue
    def peek(self) -> Optional[Dict]:
        """Look at next message without removing it."""
        with self._lock:
            if not self._queue.empty():
                msg = self._queue.queue[0]
                print(f"  [PEEK] '{self.name}' next: {msg['body']} (from {msg['sender']})")
                return msg
        print(f"  [PEEK] '{self.name}' is empty")
        return None

    def size(self) -> int:
        return self._queue.qsize()

    def is_empty(self) -> bool:
        print(f"  [EMPTY?] '{self.name}' is empty: {self._queue.empty()}")
        return self._queue.empty()


# GUI Application to demonstrate the BasicMessageQueue
class RestaurantOrderApp:

    PROCESSING_DELAY = 10.0  # seconds the kitchen takes per order

    def __init__(self, root):
        self.root = root
        self.root.title("JAZL's Pizzeria: Order System")

        self.queue = BasicMessageQueue("KitchenOrders")

        self.setup_customer_ui()
        self.setup_kitchen_ui()
        self.setup_queue_status_ui()  # queue depth counter

        self.running = True
        self.processor_thread = threading.Thread(target=self.kitchen_worker, daemon=True)
        self.processor_thread.start()

        self.update_queue_depth()

    def setup_customer_ui(self):
        frame = ttk.LabelFrame(self.root, text="Place Order (Customer App)")
        frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        ttk.Label(frame, text="Table Number:").pack(pady=2)
        self.table_entry = ttk.Entry(frame)
        self.table_entry.pack(pady=5)

        ttk.Label(frame, text="Select Dish:").pack(pady=2)
        self.dish_var = tk.StringVar()
        self.dish_box = ttk.Combobox(frame, textvariable=self.dish_var)
        self.dish_box['values'] = ("Pepperoni Pizza", 
                                   "Hawaiian Deluxe", 
                                   "All-Meat Pizza", 
                                   "Triple Cheese Pizza", 
                                   "Ham & Cheese Pizza", 
                                   "Veggie Burger", 
                                   "Caesar Salad", 
                                   "Pasta Carbonara"
                                   )
        self.dish_box.pack(pady=5)

        ttk.Button(frame, text="Send to Kitchen", command=self.place_order).pack(pady=10)

    def setup_kitchen_ui(self):
        frame = ttk.LabelFrame(self.root, text="Kitchen Monitor")
        frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        # Pending orders (queue)
        ttk.Label(frame, text="Pending Orders:").pack(anchor="w", padx=5)
        self.kitchen_list = tk.Listbox(frame, width=40, height=8)
        self.kitchen_list.pack(padx=5, pady=(0, 8))

        # Processed orders list
        ttk.Label(frame, text="Processed Orders:").pack(anchor="w", padx=5)
        self.processed_list = tk.Listbox(frame, width=40, height=8)
        self.processed_list.pack(padx=5, pady=(0, 5))

        # Peek at next order button
        ttk.Button(frame, text="See Next Order", command=self.peek_order).pack(pady=(5, 2))
        self.peek_var = tk.StringVar(value="Next up: —")
        ttk.Label(frame, textvariable=self.peek_var, foreground="blue").pack(pady=(0, 5))

    def setup_queue_status_ui(self):
        """Status bar showing live queue depth and kitchen state."""
        frame = ttk.LabelFrame(self.root, text="Queue Status")
        frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

        self.depth_var = tk.StringVar(value="Queue depth: 0")
        self.status_var = tk.StringVar(value="Kitchen: idle")

        ttk.Label(frame, textvariable=self.depth_var, font=("TkDefaultFont", 11, "bold")).pack(side="left", padx=20, pady=6)
        ttk.Label(frame, textvariable=self.status_var).pack(side="left", padx=20, pady=6)


    # Order logic
    def place_order(self):
        table = self.table_entry.get().strip()
        dish  = self.dish_var.get()

        if table and dish:
            self.queue.send(sender=f"Table {table}", body=dish)
            self.kitchen_list.insert(tk.END, f"{dish} — Table {table}")
            self.table_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("Input Error", "Please enter Table and Dish!")

    def kitchen_worker(self):
        """Runs in a background thread. Pulls orders and simulates cooking."""
        while self.running:
            order = self.queue.receive(timeout=1.0)
            if order:
                dish   = order['body']
                sender = order['sender']

                # Mark kitchen as busy
                self.root.after(0, lambda d=dish: self.status_var.set(f"Kitchen: cooking {d}…"))

                # imulate cooking time
                time.sleep(self.PROCESSING_DELAY)

                # Move order from pending to processed 
                self.root.after(0, lambda d=dish, s=sender: self._mark_order_done(d, s))
            else:
                # empty queue, mark kitchen as idle
                self.root.after(0, lambda: self.status_var.set("Kitchen: idle"))

    def _mark_order_done(self, dish: str, sender: str):
        """Called on the main thread. Removes from pending list, adds to processed."""
        # Remove the first matching entry in the pending list
        for i in range(self.kitchen_list.size()):
            if dish in self.kitchen_list.get(i) and sender.replace("Table ", "") in self.kitchen_list.get(i):
                self.kitchen_list.delete(i)
                break

        self.processed_list.insert(tk.END, f"{dish} — {sender}")
        self.processed_list.see(tk.END) 

    def peek_order(self):
        msg = self.queue.peek()
        if msg:
            self.peek_var.set(f"Next up: {msg['body']} — {msg['sender']}")
        else:
            self.peek_var.set("Queue is empty.")

    # Updates the queue depth display every 500ms
    def update_queue_depth(self):
        depth = self.queue.size()
        self.depth_var.set(f"Queue depth: {depth}")
        self.root.after(500, self.update_queue_depth)


if __name__ == "__main__":
    root = tk.Tk()
    app = RestaurantOrderApp(root)
    root.mainloop()