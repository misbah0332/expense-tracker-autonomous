"""Shared date-filter checks."""

from datetime import date

from app.exceptions import BadRequestError


def ensure_date_order(date_from: date | None, date_to: date | None) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise BadRequestError("date_from must be on or before date_to")
