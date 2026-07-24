"""Pricing unit tests."""

from decimal import Decimal

import pytest
from ecommerce.pricing import discount_amount, final_total


def test_valid_discount_amount() -> None:
    assert discount_amount(Decimal("100.00"), Decimal(10)) == Decimal("10.00")


def test_valid_final_total() -> None:
    assert final_total(Decimal("100.00"), Decimal(25)) == Decimal("75.00")


def test_discount_percent_above_100_is_rejected() -> None:
    with pytest.raises(ValueError, match="discount percent"):
        final_total(Decimal("100.00"), Decimal(150))


def test_discount_percent_below_zero_is_rejected() -> None:
    with pytest.raises(ValueError, match="discount percent"):
        discount_amount(Decimal("100.00"), Decimal(-5))
