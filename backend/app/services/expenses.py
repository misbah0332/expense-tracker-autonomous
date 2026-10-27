"""Create, list, update, and delete expenses."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models import Expense
from app.money import money
from app.services.categories import require_category


def list_expenses(
    db: Session,
    *,
    date_from: date | None,
    date_to: date | None,
    category_id: int | None,
) -> list[Expense]:
    if category_id is not None:
        require_category(db, category_id)

    query = db.query(Expense)
    query = _apply_filters(query, date_from=date_from, date_to=date_to, category_id=category_id)
    return query.order_by(Expense.expense_date.desc(), Expense.id.desc()).all()


def get_expense(db: Session, expense_id: int) -> Expense:
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise NotFoundError("Expense not found")
    return expense


def create_expense(
    db: Session,
    *,
    amount: Decimal,
    expense_date: date,
    category_id: int,
    description: str,
) -> Expense:
    require_category(db, category_id)
    expense = Expense(
        amount=money(amount),
        expense_date=expense_date,
        category_id=category_id,
        description=description,
    )
    db.add(expense)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise NotFoundError("Expense could not be saved") from None
    db.refresh(expense)
    return expense


def update_expense(
    db: Session,
    expense_id: int,
    *,
    amount: Decimal,
    expense_date: date,
    category_id: int,
    description: str,
) -> Expense:
    expense = get_expense(db, expense_id)
    require_category(db, category_id)
    expense.amount = money(amount)
    expense.expense_date = expense_date
    expense.category_id = category_id
    expense.description = description
    expense.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise NotFoundError("Expense could not be saved") from None
    db.refresh(expense)
    return expense


def delete_expense(db: Session, expense_id: int) -> None:
    expense = get_expense(db, expense_id)
    db.delete(expense)
    db.commit()


def _apply_filters(query, *, date_from: date | None, date_to: date | None, category_id: int | None):
    if date_from is not None:
        query = query.filter(Expense.expense_date >= date_from)
    if date_to is not None:
        query = query.filter(Expense.expense_date <= date_to)
    if category_id is not None:
        query = query.filter(Expense.category_id == category_id)
    return query
