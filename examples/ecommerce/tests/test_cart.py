"""Cart unit tests."""

from decimal import Decimal

import pytest
from ecommerce.cart import Cart


def test_add_item_and_subtotal() -> None:
    cart = Cart()
    cart.add_item("sku-a", Decimal("10.00"), 2)
    cart.add_item("sku-b", Decimal("5.50"), 1)

    assert cart.subtotal() == Decimal("25.50")
    assert len(cart.items) == 2


def test_add_item_rejects_non_positive_quantity() -> None:
    cart = Cart()

    with pytest.raises(ValueError, match="quantity must be positive"):
        cart.add_item("sku-a", Decimal("10.00"), 0)
