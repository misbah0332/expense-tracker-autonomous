# Architecture: Expense Tracker

## Layers
- **Frontend:** Streamlit UI.
- **Backend:** FastAPI routes, validation, business logic, and authentication.
- **Database:** PostgreSQL persistence.

## Data Flow
Streamlit communicates with FastAPI over HTTP. FastAPI accesses PostgreSQL. The frontend must never connect directly to the database.

## Structure
Keep frontend and backend separate. Organize backend code into routes, services, database access, and configuration. Keep tests and setup documentation easy to find.

## Authentication and Security
- Use JWT bearer tokens with expiration to protect expense and category endpoints.
- Store passwords as secure hashes; never store plaintext passwords.
- Validate requests on the backend and restrict database permissions.
- Store secrets in environment variables or an untracked `.env` file. Never commit secrets.
