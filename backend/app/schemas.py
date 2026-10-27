"""Request and response models. Amounts are decimals so cents are not lost to binary floats."""

import math
import re
import unicodedata
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator

from app.money import MAX_AMOUNT

Money = Annotated[
    Decimal,
    PlainSerializer(lambda value: format(value, "f"), return_type=str, when_used="json"),
]

_CATEGORY_NAME = re.compile(r"[^\W_]+(?:[ '&-]+[^\W_]+)*", flags=re.UNICODE)


def parse_amount(value: object) -> Decimal:
    if isinstance(value, bool) or value is None or isinstance(value, (list, dict)):
        raise ValueError("amount must be a positive decimal with at most 2 decimal places")

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("amount must be a positive decimal with at most 2 decimal places")
        rendered = format(value, ".2f")
        if abs(value - float(rendered)) > 1e-8:
            raise ValueError("amount must have at most 2 decimal places")
        amount = Decimal(rendered)
    else:
        try:
            amount = Decimal(str(value).strip())
        except (InvalidOperation, ValueError):
            raise ValueError(
                "amount must be a positive decimal with at most 2 decimal places"
            ) from None
        if not amount.is_finite():
            raise ValueError("amount must be a positive decimal with at most 2 decimal places")
        scaled = amount.quantize(Decimal("0.01"))
        if amount != scaled:
            raise ValueError("amount must have at most 2 decimal places")
        amount = scaled

    if amount <= 0:
        raise ValueError("amount must be greater than 0")
    if amount > MAX_AMOUNT:
        raise ValueError("amount must be at most 99999999.99")
    return amount


def clean_description(value: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError("description is required")
    if len(cleaned) > 500:
        raise ValueError("description must be at most 500 characters")
    if any(unicodedata.category(character) == "Cc" for character in cleaned):
        raise ValueError("description cannot contain control characters")
    return cleaned


def clean_category_name(value: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned or len(cleaned) > 40 or _CATEGORY_NAME.fullmatch(cleaned) is None:
        raise ValueError(
            "name must be 1-40 characters and use letters, numbers, spaces, apostrophes, or hyphens"
        )
    return cleaned


def validate_expense_date(value: date) -> date:
    earliest = date(2000, 1, 1)
    latest = date.today() + timedelta(days=365)
    if value < earliest or value > latest:
        raise ValueError("expense_date must be between 2000-01-01 and one year from today")
    return value


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=72)

    @field_validator("username")
    @classmethod
    def strip_username(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("username is required")
        return cleaned


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserRead(BaseModel):
    username: str

    model_config = ConfigDict(from_attributes=True)


class CategoryCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return clean_category_name(value)


class CategoryRead(BaseModel):
    id: int
    name: str
    is_predefined: bool

    model_config = ConfigDict(from_attributes=True)


class ExpenseWrite(BaseModel):
    amount: Decimal
    expense_date: date
    category_id: int = Field(gt=0)
    description: str

    @field_validator("amount", mode="before")
    @classmethod
    def normalize_amount(cls, value: object) -> Decimal:
        return parse_amount(value)

    @field_validator("expense_date")
    @classmethod
    def check_date(cls, value: date) -> date:
        return validate_expense_date(value)

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        return clean_description(value)


class ExpenseRead(BaseModel):
    id: int
    amount: Money
    expense_date: date
    category_id: int
    category_name: str
    description: str

    model_config = ConfigDict(from_attributes=True)


class CategoryTotal(BaseModel):
    category_id: int
    category_name: str
    total: Money
    count: int


class SummaryRead(BaseModel):
    total: Money
    expense_count: int
    by_category: list[CategoryTotal]
