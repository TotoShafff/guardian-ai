"""Shopping cart model and subtotal calculation."""

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class CartItem:
    """One line item in a shopping cart."""

    product_id: str
    unit_price: Decimal
    quantity: int


@dataclass
class Cart:
    """In-memory shopping cart."""

    items: list[CartItem] = field(default_factory=list)

    def add_item(self, product_id: str, unit_price: Decimal, quantity: int) -> None:
        """Append a product line to the cart.

        Raises:
            ValueError: if quantity is not positive.
        """
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        self.items.append(
            CartItem(product_id=product_id, unit_price=unit_price, quantity=quantity)
        )

    def subtotal(self) -> Decimal:
        """Return the sum of unit_price * quantity for every item."""
        total = Decimal(0)
        for item in self.items:
            total += item.unit_price * item.quantity
        return total
