"""Authentication, logout, and public routes."""

from datetime import timedelta

import pytest

from app.security import create_access_token
from tests.helpers import TEST_PASSWORD, TEST_USERNAME

PROTECTED = [
    ("GET", "/api/categories", None),
    ("POST", "/api/categories", {"name": "Coffee"}),
    ("DELETE", "/api/categories/1", None),
    ("GET", "/api/expenses", None),
    ("POST", "/api/expenses", {"amount": "1.00", "expense_date": "2024-01-01", "category_id": 1, "description": "x"}),
    ("GET", "/api/expenses/1", None),
    ("PUT", "/api/expenses/1", {"amount": "1.00", "expense_date": "2024-01-01", "category_id": 1, "description": "x"}),
    ("DELETE", "/api/expenses/1", None),
    ("GET", "/api/summary", None),
    ("GET", "/api/auth/me", None),
    ("POST", "/api/auth/logout", None),
]


def test_login_returns_bearer_token(client):
    response = client.post(
        "/api/auth/login",
        json={"username": f"  {TEST_USERNAME}  ", "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json() == {"username": TEST_USERNAME}


def test_login_hides_whether_the_account_exists(client):
    wrong_password = client.post(
        "/api/auth/login",
        json={"username": TEST_USERNAME, "password": "not-the-password"},
    )
    missing_user = client.post(
        "/api/auth/login",
        json={"username": "nobody", "password": "not-the-password"},
    )
    assert wrong_password.status_code == 401
    assert missing_user.status_code == 401
    assert wrong_password.json()["detail"] == missing_user.json()["detail"]


@pytest.mark.parametrize(("method", "path", "payload"), PROTECTED)
def test_protected_routes_reject_missing_token(client, method, path, payload):
    response = client.request(method, path, json=payload)
    assert response.status_code == 401


def test_invalid_token_is_rejected(client):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401


def test_expired_token_is_rejected(client):
    token, _ = create_access_token(TEST_USERNAME, expires_delta=timedelta(minutes=-5))
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Token has expired"


def test_logout_revokes_the_token(client, auth_header):
    assert client.get("/api/auth/me", headers=auth_header).status_code == 200
    logout = client.post("/api/auth/logout", headers=auth_header)
    assert logout.status_code == 204
    assert logout.content == b""
    rejected = client.get("/api/auth/me", headers=auth_header)
    assert rejected.status_code == 401
    assert rejected.json()["detail"] == "Token has been revoked"
    fresh = client.post(
        "/api/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert fresh.status_code == 200


def test_health_and_root_are_public(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/").status_code == 200


def test_malformed_expense_without_token_is_unauthorized(client):
    response = client.post("/api/expenses", json={"amount": "nope"})
    assert response.status_code == 401
