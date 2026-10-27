"""Spending totals stay exact across categories and date boundaries."""

from decimal import Decimal

from tests.helpers import sample_expense


def _money(value) -> Decimal:
    return Decimal(str(value))


def test_summary_totals_and_date_boundaries(client, auth_header, category_ids):
    food = category_ids["Food"]
    transport = category_ids["Transport"]
    rows = [
        sample_expense(food, amount="10.10", expense_date="2024-01-01", description="Groceries"),
        sample_expense(food, amount="0.20", expense_date="2024-01-31", description="Snack"),
        sample_expense(transport, amount="5.00", expense_date="2024-02-01", description="Bus"),
    ]
    for payload in rows:
        assert client.post("/api/expenses", headers=auth_header, json=payload).status_code == 201

    january = client.get(
        "/api/summary",
        headers=auth_header,
        params={"date_from": "2024-01-01", "date_to": "2024-01-31"},
    )
    assert january.status_code == 200
    body = january.json()
    assert _money(body["total"]) == Decimal("10.30")
    assert body["expense_count"] == 2
    assert len(body["by_category"]) == 1
    assert body["by_category"][0]["category_name"] == "Food"
    assert _money(body["by_category"][0]["total"]) == Decimal("10.30")
    assert body["by_category"][0]["count"] == 2

    both = client.get(
        "/api/summary",
        headers=auth_header,
        params={"date_from": "2024-01-01", "date_to": "2024-02-01"},
    ).json()
    assert _money(both["total"]) == Decimal("15.30")
    assert both["expense_count"] == 3
    assert [row["category_name"] for row in both["by_category"]] == ["Food", "Transport"]
    assert sum(_money(row["total"]) for row in both["by_category"]) == Decimal("15.30")

    single_day = client.get(
        "/api/summary",
        headers=auth_header,
        params={"date_from": "2024-02-01", "date_to": "2024-02-01"},
    ).json()
    assert _money(single_day["total"]) == Decimal("5.00")
    assert single_day["by_category"][0]["category_name"] == "Transport"

    empty = client.get(
        "/api/summary",
        headers=auth_header,
        params={"date_from": "2024-03-01", "date_to": "2024-03-31"},
    ).json()
    assert _money(empty["total"]) == Decimal("0.00")
    assert empty["expense_count"] == 0
    assert empty["by_category"] == []


def test_summary_rejects_reversed_dates(client, auth_header):
    response = client.get(
        "/api/summary",
        headers=auth_header,
        params={"date_from": "2024-05-02", "date_to": "2024-05-01"},
    )
    assert response.status_code == 422
