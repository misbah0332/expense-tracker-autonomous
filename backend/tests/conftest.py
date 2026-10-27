"""PostgreSQL fixtures. Tests use a separate database and a restricted login role."""

import os
from pathlib import Path
from urllib.parse import quote_plus

import pytest
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
_file_env = dotenv_values(ROOT / ".env")
ADMIN_URL = (
    os.environ.get("DATABASE_ADMIN_URL")
    or _file_env.get("DATABASE_ADMIN_URL")
    or "postgresql+psycopg://postgres:postgres@localhost:5433/postgres"
)
TEST_DB_NAME = "expense_tracker_test"
TEST_APP_USER = "expense_app_test"
TEST_APP_PASSWORD = "test-app-password-123"
_admin = make_url(ADMIN_URL)
TEST_DATABASE_URL = (
    f"postgresql+psycopg://{quote_plus(TEST_APP_USER)}:{quote_plus(TEST_APP_PASSWORD)}"
    f"@{_admin.host or 'localhost'}:{_admin.port or 5432}/{TEST_DB_NAME}"
)

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["JWT_SECRET"] = "test-jwt-secret-key-must-be-32-chars-min"
os.environ["JWT_EXPIRE_MINUTES"] = "60"

from app.main import app  # noqa: E402
from app.models import Category, Expense, RevokedToken  # noqa: E402
from app.setup_db import setup_database  # noqa: E402
from tests.helpers import TEST_PASSWORD, TEST_USERNAME  # noqa: E402


def _wipe(engine) -> None:
    with Session(engine) as session:
        session.execute(delete(Expense))
        session.execute(delete(Category).where(Category.is_predefined.is_(False)))
        session.execute(delete(RevokedToken))
        session.commit()


@pytest.fixture(scope="session")
def ready_database():
    setup_database(
        admin_url=ADMIN_URL,
        app_url=TEST_DATABASE_URL,
        db_name=TEST_DB_NAME,
        app_user=TEST_APP_USER,
        app_password=TEST_APP_PASSWORD,
        username=TEST_USERNAME,
        password=TEST_PASSWORD,
    )


@pytest.fixture(scope="session")
def admin_engine(ready_database):
    engine = create_engine(
        make_url(ADMIN_URL).set(database=TEST_DB_NAME),
        pool_pre_ping=True,
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def app_engine(ready_database):
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def admin_session(admin_engine):
    session = Session(admin_engine)
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(autouse=True)
def clean_rows(admin_engine):
    _wipe(admin_engine)
    yield
    _wipe(admin_engine)


@pytest.fixture
def client(ready_database, clean_rows):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_header(client):
    response = client.post(
        "/api/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def category_ids(client, auth_header):
    response = client.get("/api/categories", headers=auth_header)
    assert response.status_code == 200, response.text
    return {category["name"]: category["id"] for category in response.json()}
