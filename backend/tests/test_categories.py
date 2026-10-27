"""Predefined and custom categories."""

from app.seed_data import PREDEFINED_CATEGORIES


def test_predefined_categories_are_seeded(client, auth_header):
    response = client.get("/api/categories", headers=auth_header)
    assert response.status_code == 200
    categories = response.json()
    predefined = [category for category in categories if category["is_predefined"]]
    assert [category["name"] for category in predefined] == sorted(PREDEFINED_CATEGORIES)


def test_create_and_delete_custom_category(client, auth_header):
    created = client.post("/api/categories", headers=auth_header, json={"name": "  Coffee  Beans "})
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Coffee Beans"
    assert body["is_predefined"] is False

    conflict = client.post("/api/categories", headers=auth_header, json={"name": "coffee beans"})
    assert conflict.status_code == 409

    deleted = client.delete(f"/api/categories/{body['id']}", headers=auth_header)
    assert deleted.status_code == 204
    missing = client.delete(f"/api/categories/{body['id']}", headers=auth_header)
    assert missing.status_code == 404


def test_custom_name_cannot_shadow_a_predefined_category(client, auth_header):
    response = client.post("/api/categories", headers=auth_header, json={"name": "food"})
    assert response.status_code == 409


def test_invalid_category_names_are_rejected(client, auth_header):
    for name in ("", "   ", "Bad@Name", "x" * 41):
        response = client.post("/api/categories", headers=auth_header, json={"name": name})
        assert response.status_code == 422, name


def test_predefined_category_cannot_be_deleted(client, auth_header, category_ids):
    response = client.delete(f"/api/categories/{category_ids['Food']}", headers=auth_header)
    assert response.status_code == 403


def test_category_in_use_cannot_be_deleted(client, auth_header, category_ids):
    created = client.post("/api/categories", headers=auth_header, json={"name": "Coffee"})
    assert created.status_code == 201
    category_id = created.json()["id"]
    expense = client.post(
        "/api/expenses",
        headers=auth_header,
        json={
            "amount": "4.00",
            "expense_date": "2024-05-01",
            "category_id": category_id,
            "description": "Latte",
        },
    )
    assert expense.status_code == 201
    blocked = client.delete(f"/api/categories/{category_id}", headers=auth_header)
    assert blocked.status_code == 409
    assert client.delete(f"/api/expenses/{expense.json()['id']}", headers=auth_header).status_code == 204
    assert client.delete(f"/api/categories/{category_id}", headers=auth_header).status_code == 204
    assert category_ids["Food"]
