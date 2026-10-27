"""Spending totals for a date range."""

from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Category, Expense
from app.money import money


def spending_summary(
    db: Session,
    *,
    date_from: date | None,
    date_to: date | None,
) -> dict:
    total = db.query(func.coalesce(func.sum(Expense.amount), 0))
    count = db.query(func.count(Expense.id))
    grouped = db.query(
        Category.id,
        Category.name,
        func.sum(Expense.amount),
        func.count(Expense.id),
    ).join(Expense, Expense.category_id == Category.id)

    total = _apply_dates(total, date_from, date_to)
    count = _apply_dates(count, date_from, date_to)
    grouped = _apply_dates(grouped, date_from, date_to)

    rows = grouped.group_by(Category.id, Category.name).order_by(func.sum(Expense.amount).desc()).all()
    by_category = [
        {
            "category_id": category_id,
            "category_name": name,
            "total": money(total_amount or 0),
            "count": row_count,
        }
        for category_id, name, total_amount, row_count in rows
    ]
    expense_count = int(count.scalar() or 0)
    return {
        "total": money(Decimal(total.scalar() or 0)),
        "expense_count": expense_count,
        "by_category": by_category,
    }


def _apply_dates(query, date_from: date | None, date_to: date | None):
    if date_from is not None:
        query = query.filter(Expense.expense_date >= date_from)
    if date_to is not None:
        query = query.filter(Expense.expense_date <= date_to)
    return query
