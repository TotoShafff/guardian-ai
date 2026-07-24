"""Price and discount helpers using Decimal money amounts."""

import os
from decimal import Decimal


def discount_amount(subtotal: Decimal, percent: Decimal) -> Decimal:
    """Return the absolute discount for ``percent`` of ``subtotal``."""
    return (subtotal * percent) / Decimal(100)


def final_total(subtotal: Decimal, percent: Decimal) -> Decimal:
    """Return subtotal minus the percentage discount."""
    return subtotal - discount_amount(subtotal, percent)
