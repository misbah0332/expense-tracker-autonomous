"""Expense create, read, update, delete, and filters."""

from decimal import Decimal

from tests.helpers import sample_expense


def _money(value) -> Decimal:
    return Decimal(str(value))


def test_expense_crud_and_filters(client, auth_header, category_ids):
    food = category_ids["Food"]
    transport = category_ids["Transport"]
    created = client.post(
        "/api/expenses",
        headers=auth_header,
        json=sample_expense(food, amount="10.10", description="  Team   lunch  "),
    )
    assert created.status_code == 201
    body = created.json()
    assert _money(body["amount"]) == Decimal("10.10")
    assert body["description"] == "Team lunch"
    assert body["category_name"] == "Food"
    expense_id = body["id"]

    second = client.post(
        "/api/expenses",
        headers=auth_header,
        json=sample_expense(
            transport,
            amount="5.00",
            expense_date="2024-02-01",
            description="Train",
        ),
    )
    assert second.status_code == 201

    fetched = client.get(f"/api/expenses/{expense_id}", headers=auth_header)
    assert fetched.status_code == 200
    assert fetched.json()["description"] == "Team lunch"

    january = client.get(
        "/api/expenses",
        headers=auth_header,
        params={"date_from": "2024-06-01", "date_to": "2024-06-30", "category_id": food},
    )
    assert january.status_code == 200
    assert [row["id"] for row in january.json()] == [expense_id]

    updated = client.put(
        f"/api/expenses/{expense_id}",
        headers=auth_header,
        json=sample_expense(transport, amount="8.25", description="Taxi"),
    )
    assert updated.status_code == 200
    assert updated.json()["category_name"] == "Transport"
    assert _money(updated.json()["amount"]) == Decimal("8.25")

    deleted = client.delete(f"/api/expenses/{expense_id}", headers=auth_header)
    assert deleted.status_code == 204
    assert client.get(f"/api/expenses/{expense_id}", headers=auth_header).status_code == 404


def test_missing_expense_is_not_found(client, auth_header, category_ids):
    missing = client.put(
        "/api/expenses/999999",
        headers=auth_header,
        json=sample_expense(category_ids["Food"]),
    )
    assert missing.status_code == 404
    assert client.delete("/api/expenses/999999", headers=auth_header).status_code == 404


def test_date_filter_must_be_ordered(client, auth_header):
    response = client.get(
        "/api/expenses",
        headers=auth_header,
        params={"date_from": "2024-02-01", "date_to": "2024-01-01"},
    )
    assert response.status_code == 422
    assert "date_from" in response.json()["detail"]
