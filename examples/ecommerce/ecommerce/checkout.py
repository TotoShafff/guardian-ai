"""Checkout orchestration over cart, inventory, and pricing."""

from dataclasses import dataclass
from decimal import Decimal

from ecommerce.cart import Cart
from ecommerce.inventory import Inventory
from ecommerce.pricing import discount_amount, final_total


@dataclass(frozen=True)
class CheckoutResult:
    """Outcome of a successful checkout attempt."""

    subtotal: Decimal
    discount: Decimal
    total: Decimal


def checkout(cart: Cart, inventory: Inventory, discount_percent: Decimal) -> CheckoutResult:
    """Validate stock, reserve it, apply discount, and return totals.

    Args:
        cart: Cart whose items will be purchased.
        inventory: Stock source used for reservation.
        discount_percent: Percentage discount to apply (intended range: 0..100).

    Returns:
        CheckoutResult with subtotal, discount amount, and final total.
    """
    for item in cart.items:
        available = inventory.get_stock(item.product_id)
        if available < item.quantity:
            raise ValueError(
                f"insufficient stock for {item.product_id}: "
                f"need {item.quantity}, have {available}"
            )

    for item in cart.items:
        inventory.reserve(item.product_id, item.quantity)

    subtotal = cart.subtotal()
    discount = discount_amount(subtotal, discount_percent)
    total = final_total(subtotal, discount_percent)
    return CheckoutResult(subtotal=subtotal, discount=discount, total=total)


def format_money(amount: Decimal) -> str:
    return f"{amount.quantize(Decimal('0.01'))}"
