"""In-memory product stock tracking."""


class Inventory:
    """Simple stock ledger keyed by product_id."""

    def __init__(self, initial_stock: dict[str, int] | None = None) -> None:
        self._stock: dict[str, int] = dict(initial_stock or {})

    def get_stock(self, product_id: str) -> int:
        """Return available units for ``product_id`` (0 if unknown)."""
        return self._stock.get(product_id, 0)

    def reserve(self, product_id: str, quantity: int) -> None:
        """Reserve ``quantity`` units of ``product_id`` from available stock."""
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        current = self._stock.get(product_id, 0)
        self._stock[product_id] = current - quantity
