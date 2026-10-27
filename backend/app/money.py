"""Decimal helpers so money is stored and returned with cent precision."""

from decimal import ROUND_HALF_UP, Decimal

TWOPLACES = Decimal("0.01")
MAX_AMOUNT = Decimal("99999999.99")


def money(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
