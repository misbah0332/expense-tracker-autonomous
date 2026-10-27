# Expense Tracker

Single-user expense tracker. The Streamlit UI talks to a FastAPI backend, and the backend stores data in PostgreSQL. The UI never connects to the database.

You can sign in, record expenses (amount, date, category, and description), add custom categories alongside the built-in ones, and view total and category spending for a date range.

## Prerequisites

- Python 3.14 (3.12+ should also work)
- Docker Desktop, for the PostgreSQL database

A local PostgreSQL install often already uses port 5432. This project's database is published on **port 5433** so the two can run at the same time.

## Setup

From the project root in PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d
```

Edit `.env` and replace `JWT_SECRET`, `APP_PASSWORD`, and `DB_APP_PASSWORD` before storing real expenses. Keep `POSTGRES_PASSWORD`, the password inside `DATABASE_ADMIN_URL`, and `DB_APP_PASSWORD` / `DATABASE_URL` in sync. URL-encode any password character that is not a letter or number.

Wait until the database is healthy, then create the restricted role, tables, and the single login account:

```powershell
docker compose ps
cd backend
python -m app.setup_db
```

`APP_USERNAME` and `APP_PASSWORD` in `.env` are the only account. Running setup again resets that password to the value in `.env`. There is no registration screen.

Built-in categories: Food, Transport, Housing, Utilities, Healthcare, Entertainment, Shopping, Personal, Education, and Other.

## Run

Use two terminals with the virtual environment activated.

Backend, from `backend`:

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs

Frontend, from `frontend`:

```powershell
streamlit run app.py
```

App: http://127.0.0.1:8501

Sign in with `APP_USERNAME` and `APP_PASSWORD`. Log out from the sidebar. Logout revokes that token; signing in again issues a new one.

## Tests

Docker must be up. From the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Pytest creates `expense_tracker_test` and a separate restricted role (`expense_app_test`). It does not use the development account password. The suite covers login and logout, rejected unauthenticated calls, expense and category behavior, date filters and summary totals, validation, password hashing, and database privileges.

## Security

- Passwords are stored as bcrypt hashes. The API never returns the hash.
- Expense, category, summary, and logout routes require a JWT bearer token with an expiry. Logout stores the token id in `revoked_tokens` until it expires.
- Failed logins use the same response for an unknown user and a wrong password.
- Request bodies are validated in the API. Amounts are decimals with at most two places. The database also checks amount, description length, and the minimum date.
- The API connects as `expense_app`, which is not a superuser. That role can read the user row and change expenses, custom categories, and revoked tokens. It cannot create tables, change the password hash, insert another user, or delete predefined categories. Row-level security and a trigger enforce the category rules.
- Only one user row is allowed. Multiple users, budgets, recurring expenses, bank imports, and AI features are out of scope.
- Secrets belong in `.env`, which is gitignored. `.env.example` has local placeholders only.

Date filters are inclusive. An expense on either endpoint of the range is included. Summary totals are the sum of the category totals for that range.

## API

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/api/auth/login` | No | Exchange username and password for a bearer token |
| POST | `/api/auth/logout` | Yes | Revoke the current token |
| GET | `/api/auth/me` | Yes | Current username |
| GET | `/api/categories` | Yes | List categories |
| POST | `/api/categories` | Yes | Add a custom category |
| DELETE | `/api/categories/{id}` | Yes | Delete an unused custom category |
| GET | `/api/expenses` | Yes | List expenses, with optional `date_from`, `date_to`, and `category_id` |
| POST | `/api/expenses` | Yes | Create an expense |
| GET | `/api/expenses/{id}` | Yes | Fetch one expense |
| PUT | `/api/expenses/{id}` | Yes | Replace an expense |
| DELETE | `/api/expenses/{id}` | Yes | Delete an expense |
| GET | `/api/summary` | Yes | Total and per-category spending for an optional date range |
| GET | `/health` | No | Database connectivity check |

## Project layout

```
backend/app          FastAPI routes, services, models, database setup
backend/tests        API and permission tests
frontend             Streamlit UI and HTTP client
docker-compose.yml   Local PostgreSQL
```

## Troubleshooting

- `Could not connect to PostgreSQL`: start Docker Desktop, then `docker compose up -d`, and wait until `docker compose ps` shows healthy.
- Port 8000 or 8501 is already in use: start the API with `uvicorn app.main:app --host 127.0.0.1 --port 8001`, set `API_BASE_URL=http://127.0.0.1:8001`, and start Streamlit with `streamlit run app.py --server.port 8502`.
- Port 5433 is already in use: change `POSTGRES_PORT` and the port in both database URLs in `.env`.
- The API exits saying the database is not initialized: run `python -m app.setup_db` from `backend`.
- Login works in the API and the UI says it cannot reach the API: start uvicorn on port 8000, or set `API_BASE_URL`.
- Example passwords are still in `.env`: setup prints a warning. Change them before entering real expenses.
