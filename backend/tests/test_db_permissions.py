"""The application role cannot change schema, users, or predefined categories."""

import pytest
from psycopg.errors import InsufficientPrivilege
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.models import User
from app.security import verify_password
from app.seed_data import PREDEFINED_CATEGORIES
from tests.helpers import TEST_PASSWORD


def test_password_is_stored_as_a_hash(admin_session):
    user = admin_session.query(User).one()
    assert user.username == "tester"
    assert user.password_hash != TEST_PASSWORD
    assert user.password_hash.startswith("$2")
    assert verify_password(TEST_PASSWORD, user.password_hash)


def test_only_one_user_row_is_allowed(admin_session):
    admin_session.add(User(username="second", password_hash="not-a-real-hash"))
    with pytest.raises(IntegrityError):
        admin_session.commit()
    admin_session.rollback()


def test_app_role_cannot_create_tables(app_engine):
    with pytest.raises(ProgrammingError) as exc_info:
        with app_engine.begin() as conn:
            conn.execute(text("CREATE TABLE permission_probe (id integer)"))
    assert isinstance(exc_info.value.orig, InsufficientPrivilege)


def test_app_role_cannot_modify_users(app_engine):
    with pytest.raises(ProgrammingError) as exc_info:
        with app_engine.begin() as conn:
            conn.execute(text("UPDATE users SET password_hash = 'stolen'"))
    assert isinstance(exc_info.value.orig, InsufficientPrivilege)

    with pytest.raises(ProgrammingError):
        with app_engine.begin() as conn:
            conn.execute(
                text("INSERT INTO users (username, password_hash) VALUES ('other', 'hash')")
            )


def test_app_role_cannot_remove_predefined_categories(app_engine, admin_session):
    try:
        with app_engine.begin() as conn:
            conn.execute(text("DELETE FROM categories WHERE is_predefined = true"))
    except ProgrammingError:
        pass
    remaining = admin_session.execute(
        text("SELECT COUNT(*) FROM categories WHERE is_predefined = true")
    ).scalar_one()
    assert remaining == len(PREDEFINED_CATEGORIES)


def test_app_role_cannot_insert_predefined_category(app_engine):
    with pytest.raises(ProgrammingError) as exc_info:
        with app_engine.begin() as conn:
            conn.execute(
                text("INSERT INTO categories (name, is_predefined) VALUES ('Secret', true)")
            )
    assert isinstance(exc_info.value.orig, InsufficientPrivilege)
