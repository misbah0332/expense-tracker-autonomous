"""FastAPI application. Expense and category routes require a bearer token."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import __version__
from app.database import SessionLocal
from app.exceptions import AppError
from app.routers import auth, categories, expenses, summary

PUBLIC_PATHS = {"/", "/health", "/api/auth/login", "/openapi.json", "/docs", "/redoc"}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        with SessionLocal() as session:
            user_count = session.execute(text("SELECT COUNT(*) FROM users")).scalar_one()
            category_count = session.execute(text("SELECT COUNT(*) FROM categories")).scalar_one()
    except Exception as exc:
        raise RuntimeError(
            "Could not read the application database. Check DATABASE_URL and run "
            "`python -m app.setup_db` from the backend directory."
        ) from exc
    if user_count != 1 or category_count < 1:
        raise RuntimeError(
            "Database is not initialized. Run `python -m app.setup_db` from the backend directory."
        )
    yield


app = FastAPI(
    title="Expense Tracker API",
    version=__version__,
    lifespan=lifespan,
    redirect_slashes=False,
)


@app.middleware("http")
async def require_bearer_for_api(request: Request, call_next):
    path = request.url.path
    if path in PUBLIC_PATHS or not path.startswith("/api"):
        return await call_next(request)
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return JSONResponse(
            status_code=401,
            content={"detail": "Not authenticated"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await call_next(request)


@app.exception_handler(AppError)
async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else {}
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message}, headers=headers)


app.include_router(auth.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(expenses.router, prefix="/api")
app.include_router(summary.router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    with SessionLocal() as session:
        session.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "expense-tracker", "docs": "/docs", "health": "/health"}
