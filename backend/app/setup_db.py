"""Create the database, restricted role, schema, and seed data.

The running API uses DATABASE_URL and does not have permission to change this schema.
Run this module with the admin URL before starting the API:

    python -m app.setup_db
"""

import re
import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models import Base, Category, User
from app.security import hash_password
from app.seed_data import PREDEFINED_CATEGORIES

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,62}")
_USERNAME = re.compile(r"[A-Za-z0-9._-]{3,50}")


def setup_database(
    *,
    admin_url: str,
    app_url: str,
    db_name: str,
    app_user: str,
    app_password: str,
    username: str,
    password: str,
) -> None:
    validate_identifier(db_name, "DB_NAME")
    validate_identifier(app_user, "DB_APP_USER")
    validate_username(username)
    validate_password(password, "APP_PASSWORD")
    validate_password(app_password, "DB_APP_PASSWORD")

    wait_for_server(admin_url)
    _create_role_and_database(admin_url, db_name, app_user, app_password)

    admin_engine = create_engine(
        make_url(admin_url).set(database=db_name),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )
    Base.metadata.create_all(admin_engine)
    with admin_engine.begin() as conn:
        _apply_privileges(conn, db_name, app_user)
        _apply_category_guards(conn, app_user)
    _seed(admin_engine, username, password)
    _verify_restricted_role(admin_engine, app_url)
    admin_engine.dispose()


def main() -> None:
    settings = get_settings()
    missing = [
        name
        for name, value in (
            ("DATABASE_ADMIN_URL", settings.database_admin_url),
            ("DATABASE_URL", settings.database_url),
            ("DB_APP_PASSWORD", settings.db_app_password),
            ("APP_USERNAME", settings.app_username),
            ("APP_PASSWORD", settings.app_password),
        )
        if not value
    ]
    if missing:
        raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")

    app_url = make_url(settings.database_url)
    if app_url.database != settings.db_name:
        raise SystemExit(
            f"DATABASE_URL database '{app_url.database}' does not match DB_NAME '{settings.db_name}'."
        )
    if app_url.username != settings.db_app_user:
        raise SystemExit("DATABASE_URL user does not match DB_APP_USER.")
    if app_url.password != settings.db_app_password:
        raise SystemExit("DATABASE_URL password does not match DB_APP_PASSWORD.")

    if settings.jwt_secret.startswith("change-me") or (
        settings.app_password or ""
    ).startswith("change-me") or (settings.db_app_password or "").startswith("change-me"):
        print("Warning: an example password or JWT_SECRET is still in use. Replace it before real use.")

    assert settings.database_admin_url is not None
    assert settings.db_app_password is not None
    assert settings.app_username is not None
    assert settings.app_password is not None
    setup_database(
        admin_url=settings.database_admin_url,
        app_url=settings.database_url,
        db_name=settings.db_name,
        app_user=settings.db_app_user,
        app_password=settings.db_app_password,
        username=settings.app_username,
        password=settings.app_password,
    )
    print(f"Database {settings.db_name} is ready for user {settings.app_username}.")


def wait_for_server(admin_url: str, attempts: int = 30) -> None:
    last_error: Exception | None = None
    maintenance = make_url(admin_url).set(database="postgres")
    for _ in range(attempts):
        engine = create_engine(maintenance, connect_args={"connect_timeout": 2})
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as exc:
            last_error = exc
            time.sleep(1)
        finally:
            engine.dispose()
    raise RuntimeError(
        "Could not connect to PostgreSQL. From the project root run `docker compose up -d` "
        f"and try again. Last error: {last_error}"
    )


def validate_identifier(name: str, label: str) -> None:
    if _IDENTIFIER.fullmatch(name) is None:
        raise SystemExit(f"{label} must be a simple PostgreSQL identifier.")


def validate_username(username: str) -> None:
    if _USERNAME.fullmatch(username) is None:
        raise SystemExit(
            "APP_USERNAME must be 3-50 characters and use letters, numbers, dots, underscores, or hyphens."
        )


def validate_password(password: str, label: str) -> None:
    if password.strip() != password or len(password) < 12 or len(password) > 72:
        raise SystemExit(f"{label} must be 12 to 72 characters and cannot start or end with whitespace.")
    if len(password.encode("utf-8")) > 72:
        raise SystemExit(f"{label} must be at most 72 bytes.")


def _create_role_and_database(admin_url: str, db_name: str, app_user: str, app_password: str) -> None:
    engine = create_engine(
        make_url(admin_url).set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        connect_args={"connect_timeout": 5},
    )
    password = "'" + app_password.replace("'", "''") + "'"
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_roles WHERE rolname = :name"),
            {"name": app_user},
        ).scalar()
        attributes = (
            f"{app_user} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
            f"NOINHERIT NOREPLICATION PASSWORD {password}"
        )
        if exists:
            conn.execute(text(f"ALTER ROLE {attributes}"))
        else:
            conn.execute(text(f"CREATE ROLE {attributes}"))
        conn.execute(text(f"ALTER ROLE {app_user} SET search_path = public"))
        database_exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": db_name},
        ).scalar()
        if not database_exists:
            conn.execute(
                text(f"CREATE DATABASE {db_name} ENCODING 'UTF8' TEMPLATE template0")
            )
    engine.dispose()


def _apply_privileges(conn, db_name: str, app_user: str) -> None:
    statements = [
        f"REVOKE ALL ON DATABASE {db_name} FROM PUBLIC",
        f"GRANT CONNECT ON DATABASE {db_name} TO {app_user}",
        "REVOKE CREATE ON SCHEMA public FROM PUBLIC",
        f"REVOKE ALL ON SCHEMA public FROM {app_user}",
        f"GRANT USAGE ON SCHEMA public TO {app_user}",
        "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC",
        f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {app_user}",
        f"GRANT SELECT ON TABLE users TO {app_user}",
        f"GRANT SELECT, INSERT, DELETE ON TABLE categories TO {app_user}",
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE expenses TO {app_user}",
        f"GRANT SELECT, INSERT, DELETE ON TABLE revoked_tokens TO {app_user}",
        "REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC",
        f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {app_user}",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_single_row ON users ((true))",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_categories_name_lower ON categories (lower(name))",
    ]
    for statement in statements:
        conn.execute(text(statement))


def _apply_category_guards(conn, app_user: str) -> None:
    conn.execute(
        text(
            f"""
            CREATE OR REPLACE FUNCTION prevent_restricted_category_changes()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
              IF TG_OP = 'DELETE' AND OLD.is_predefined THEN
                RAISE EXCEPTION 'predefined categories cannot be deleted'
                  USING ERRCODE = '42501';
              END IF;
              IF TG_OP = 'UPDATE' AND OLD.is_predefined AND (
                NEW.name IS DISTINCT FROM OLD.name
                OR NEW.is_predefined IS DISTINCT FROM OLD.is_predefined
              ) THEN
                RAISE EXCEPTION 'predefined categories cannot be changed'
                  USING ERRCODE = '42501';
              END IF;
              IF TG_OP = 'INSERT' AND NEW.is_predefined AND current_user = '{app_user}' THEN
                RAISE EXCEPTION 'insufficient privilege to create a predefined category'
                  USING ERRCODE = '42501';
              END IF;
              IF TG_OP = 'DELETE' THEN
                RETURN OLD;
              END IF;
              RETURN NEW;
            END;
            $$;
            """
        )
    )
    conn.execute(text("DROP TRIGGER IF EXISTS categories_guard ON categories"))
    conn.execute(
        text(
            """
            CREATE TRIGGER categories_guard
            BEFORE INSERT OR UPDATE OR DELETE ON categories
            FOR EACH ROW
            EXECUTE FUNCTION prevent_restricted_category_changes()
            """
        )
    )
    conn.execute(text("ALTER TABLE categories ENABLE ROW LEVEL SECURITY"))
    for policy in ("categories_select", "categories_insert", "categories_delete"):
        conn.execute(text(f"DROP POLICY IF EXISTS {policy} ON categories"))
    conn.execute(
        text(
            f"""
            CREATE POLICY categories_select ON categories
            FOR SELECT TO {app_user}
            USING (true)
            """
        )
    )
    conn.execute(
        text(
            f"""
            CREATE POLICY categories_insert ON categories
            FOR INSERT TO {app_user}
            WITH CHECK (is_predefined = false)
            """
        )
    )
    conn.execute(
        text(
            f"""
            CREATE POLICY categories_delete ON categories
            FOR DELETE TO {app_user}
            USING (is_predefined = false)
            """
        )
    )


def _seed(engine: Engine, username: str, password: str) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        existing = {category.name.casefold() for category in db.query(Category).all()}
        for name in PREDEFINED_CATEGORIES:
            if name.casefold() not in existing:
                db.add(Category(name=name, is_predefined=True))
        user = db.query(User).one_or_none()
        hashed = hash_password(password)
        if user is None:
            db.add(User(username=username, password_hash=hashed))
        else:
            user.username = username
            user.password_hash = hashed
        db.commit()


def _verify_restricted_role(admin_engine: Engine, app_url: str) -> None:
    app_engine = create_engine(app_url, connect_args={"connect_timeout": 5})
    try:
        with app_engine.connect() as conn:
            count = conn.execute(
                text("SELECT COUNT(*) FROM categories WHERE is_predefined = true")
            ).scalar_one()
        if count != len(PREDEFINED_CATEGORIES):
            raise RuntimeError("Predefined categories were not seeded.")

        if _statement_succeeds(app_engine, "CREATE TABLE permission_probe (id integer)"):
            with admin_engine.begin() as conn:
                conn.execute(text("DROP TABLE IF EXISTS permission_probe"))
            raise RuntimeError("The application role can create tables. Privileges are too broad.")

        if _statement_succeeds(app_engine, "UPDATE users SET password_hash = password_hash"):
            raise RuntimeError("The application role can update users. Privileges are too broad.")

        try:
            with app_engine.begin() as conn:
                conn.execute(text("DELETE FROM categories WHERE is_predefined = true"))
        except ProgrammingError:
            pass
        with app_engine.connect() as conn:
            remaining = conn.execute(
                text("SELECT COUNT(*) FROM categories WHERE is_predefined = true")
            ).scalar_one()
        if remaining != len(PREDEFINED_CATEGORIES):
            raise RuntimeError("The application role deleted predefined categories.")
    finally:
        app_engine.dispose()


def _statement_succeeds(engine: Engine, statement: str) -> bool:
    try:
        with engine.begin() as conn:
            conn.execute(text(statement))
    except ProgrammingError:
        return False
    return True


if __name__ == "__main__":
    main()
