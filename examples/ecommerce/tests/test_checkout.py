"""Checkout and inventory integration tests."""

from decimal import Decimal

import pytest
from ecommerce.cart import Cart
from ecommerce.checkout import checkout, format_money
from ecommerce.inventory import Inventory


def test_checkout_happy_path() -> None:
    cart = Cart()
    cart.add_item("sku-a", Decimal("20.00"), 2)
    inventory = Inventory({"sku-a": 5})

    result = checkout(cart, inventory, Decimal(10))

    assert result.subtotal == Decimal("40.00")
    assert result.discount == Decimal("4.00")
    assert result.total == Decimal("36.00")
    assert inventory.get_stock("sku-a") == 3


def test_checkout_rejects_insufficient_stock() -> None:
    cart = Cart()
    cart.add_item("sku-a", Decimal("20.00"), 4)
    inventory = Inventory({"sku-a": 2})

    with pytest.raises(ValueError, match="insufficient stock"):
        checkout(cart, inventory, Decimal(0))

    assert inventory.get_stock("sku-a") == 2


def test_reserve_rejects_quantity_above_available_stock() -> None:
    inventory = Inventory({"sku-a": 3})

    with pytest.raises(ValueError, match="insufficient stock"):
        inventory.reserve("sku-a", 5)

    assert inventory.get_stock("sku-a") == 3


def test_format_money_two_decimal_places() -> None:
    assert format_money(Decimal("12.5")) == "12.50"
