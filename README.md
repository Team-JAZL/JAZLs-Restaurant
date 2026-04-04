# JAZL's Restaurant

A cozy point-of-sale demo app built for `CCS 231` showing a **basic message queue** implementation using a restaurant order system analogy.

## Overview

This project demonstrates how a producer-consumer architecture works by modeling a restaurant kitchen. The app separates concerns into modular Python files:

- `main.py` — application launcher
- `ui.py` — user interface and POS flow
- `order.py` — order data model with unique order IDs
- `message_queue.py` — queue wrapper around `queue.Queue`
- `kitchen.py` — kitchen worker that processes orders in a background thread

## What is a Basic Message Queue?

A basic message queue is a thread-safe buffer that allows one part of a system to produce messages while another part consumes them at its own pace.

In this app:

- Customers place orders through the UI.
- Orders are wrapped in a message and enqueued in the kitchen queue.
- The kitchen worker consumes orders from the queue one-by-one.
- Completed orders are shown in the processed list.

This demonstrates key queue concepts:

- **Producer**: the UI submitting orders.
- **Consumer**: the kitchen worker processing orders.
- **FIFO**: first-in, first-out ordering.
- **Backpressure**: full queue handling when the kitchen is overwhelmed.
- **Peek**: viewing the next message without consuming it.

## Architecture and Implementation

### `order.py`

Defines the `Order` dataclass:

- `dish`: menu item name
- `table_number`: the table number
- `order_id`: short unique id generated automatically

The `Order` object is the payload passed through the message queue, and the unique ID makes it safe to track duplicate items from the same table.

### `message_queue.py`

Implements `BasicMessageQueue` on top of Python's `queue.Queue`.

Key behaviors:

- `send(sender, body)` uses a non-blocking `put()` so the caller can catch `queue.Full` and warn the user.
- `receive(timeout)` blocks until the next message is available or the timeout expires.
- `peek()` looks at the next message without removing it, using internal queue access wrapped in exception handling.
- `size()` and `is_empty()` expose queue state.

### `kitchen.py`

Defines `KitchenWorker` as a background thread:

- Consumes orders from `BasicMessageQueue`
- Simulates cooking time with `time.sleep`
- Sends status updates and progress callbacks to the UI
- Handles graceful shutdown with a stop event

This separation makes the queue and processing logic independent from the UI.

### `ui.py`

Builds a touchscreen-style POS interface with:

- a numeric keypad for table selection
- a scrollable menu button grid
- a cart for batching multiple dishes
- `Submit Order`, `Clear Cart`, and `Remove Selected` actions
- kitchen monitor and processed order lists
- queue depth and kitchen status indicators
- cooking progress bar

The UI uses `ttk.Style` to create a pastel, cozy pizzeria palette and keeps the layout responsive within a 640×480 window.

### `main.py`

A minimal entrypoint that starts Tkinter and launches the `RestaurantOrderApp`.

## Setup and Run

### Prerequisites

- Python 3.8+ installed
- Tkinter available (usually included with standard Python installs on Windows)

### Running the app

Open a terminal in the project folder and run:

```bash
python main.py
```

### Testing Syntax

To verify all files compile successfully:

```bash
python -m py_compile main.py ui.py order.py message_queue.py kitchen.py
```

## Key Features

- **Modular design**: clear separation of UI, queue, order, and kitchen logic
- **Unique order IDs**: ensures duplicate orders are tracked correctly
- **Queue backpressure handling**: warns the user when the kitchen queue is full
- **Thread-safe kitchen worker**: background processing with graceful shutdown
- **UI enhancements**: pastel restaurant theme, emojis, progress bar, responsive layout

## Notes

This is a learning/demo application, not a production POS system. The focus is on illustrating how a basic message queue behaves in a restaurant-style workflow and how UI, background work, and inter-thread communication can be structured cleanly.
