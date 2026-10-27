"""Backend validation for amounts, dates, and descriptions."""

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.schemas import ExpenseWrite
from tests.helpers import sample_expense


def test_amount_model_rejects_extra_precision():
    with pytest.raises(ValidationError):
        ExpenseWrite(
            amount="1.234",
            expense_date=date(2024, 1, 1),
            category_id=1,
            description="Lunch",
        )


@pytest.mark.parametrize(
    ("overrides", "snippet"),
    [
        ({"amount": "0"}, "greater than 0"),
        ({"amount": "-5.00"}, "greater than 0"),
        ({"amount": "1.234"}, "2 decimal"),
        ({"amount": "100000000.00"}, "at most"),
        ({"amount": "abc"}, "decimal"),
        ({"description": "   "}, "required"),
        ({"description": "x" * 501}, "500"),
        ({"expense_date": "1999-12-31"}, "2000-01-01"),
        ({"expense_date": "2024-13-40"}, "date"),
        ({"category_id": 0}, "greater than 0"),
    ],
)
def test_invalid_expense_payloads(client, auth_header, category_ids, overrides, snippet):
    payload = sample_expense(category_ids["Food"])
    payload.update(overrides)
    response = client.post("/api/expenses", headers=auth_header, json=payload)
    assert response.status_code == 422
    assert snippet.lower() in response.text.lower()


def test_far_future_date_is_rejected(client, auth_header, category_ids):
    far = date.today() + timedelta(days=400)
    response = client.post(
        "/api/expenses",
        headers=auth_header,
        json=sample_expense(category_ids["Other"], expense_date=far.isoformat()),
    )
    assert response.status_code == 422


def test_unknown_category_is_rejected(client, auth_header):
    response = client.post(
        "/api/expenses",
        headers=auth_header,
        json=sample_expense(999999),
    )
    assert response.status_code == 422
    assert "category" in response.json()["detail"]


def test_integer_amount_is_accepted(client, auth_header, category_ids):
    response = client.post(
        "/api/expenses",
        headers=auth_header,
        json=sample_expense(category_ids["Other"], amount=15),
    )
    assert response.status_code == 201
    assert response.json()["amount"] in {"15.00", "15.0", "15"}
