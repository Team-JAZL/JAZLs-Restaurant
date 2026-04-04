"""
This module defines the `Order` dataclass which represents a single
restaurant order. Orders are immutable and carry a short unique id used
by the UI to disambiguate duplicates.
"""

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Order:
    """Immutable data model for an order.

    Attributes:
        dish: The name of the dish ordered.
        table_number: The table number (kept as a string).
        order_id: Short unique identifier (generated automatically).
    """
    dish: str
    table_number: str
    order_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    @property
    def sender(self) -> str:
        """Return the sender string used by the message queue (e.g., 'Table 3')."""
        return f"Table {self.table_number}"

    @property
    def description(self) -> str:
        """Full, human-friendly description including the order id used in UI lists."""
        return f"{self.dish} — {self.sender} [#{self.order_id}]"

    @property
    def short_description(self) -> str:
        """Short description without the id."""
        return f"{self.dish} — {self.sender}"
