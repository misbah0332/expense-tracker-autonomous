# PRD: Expense Tracker

## Goal
Build a secure, single-user expense tracker.

## Features
- Login and logout.
- Create, view, edit, and delete expenses.
- Store amount, date, category, and description.
- Support predefined and custom categories.
- Show total and category-wise spending with date filters.

## Stack
Python, Streamlit, FastAPI, PostgreSQL.

## Security
Hash passwords, protect API endpoints, validate inputs on the backend, restrict database permissions, and keep secrets out of source control.

## Out of Scope
Multiple users, budgets, recurring expenses, bank integrations, and AI features.

## Acceptance Criteria
- Login works and protected endpoints reject unauthenticated requests.
- Expense and category operations work correctly.
- Date filters and spending summaries return accurate results.
- Data persists in PostgreSQL.
- Automated tests cover core features, validation, and authentication.
- Setup and run instructions are documented.
