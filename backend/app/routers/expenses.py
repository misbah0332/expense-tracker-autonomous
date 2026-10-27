"""Expense CRUD and date filters."""

from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.schemas import ExpenseRead, ExpenseWrite
from app.services import expenses as expense_service
from app.services.dates import ensure_date_order

router = APIRouter(
    prefix="/expenses",
    tags=["expenses"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[ExpenseRead])
def list_expenses(
    date_from: date | None = None,
    date_to: date | None = None,
    category_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
) -> list:
    ensure_date_order(date_from, date_to)
    return expense_service.list_expenses(
        db, date_from=date_from, date_to=date_to, category_id=category_id
    )


@router.post("", response_model=ExpenseRead, status_code=201)
def create_expense(body: ExpenseWrite, db: Session = Depends(get_db)) -> object:
    return expense_service.create_expense(
        db,
        amount=body.amount,
        expense_date=body.expense_date,
        category_id=body.category_id,
        description=body.description,
    )


@router.get("/{expense_id}", response_model=ExpenseRead)
def get_expense(expense_id: int, db: Session = Depends(get_db)) -> object:
    return expense_service.get_expense(db, expense_id)


@router.put("/{expense_id}", response_model=ExpenseRead)
def update_expense(expense_id: int, body: ExpenseWrite, db: Session = Depends(get_db)) -> object:
    return expense_service.update_expense(
        db,
        expense_id,
        amount=body.amount,
        expense_date=body.expense_date,
        category_id=body.category_id,
        description=body.description,
    )


@router.delete("/{expense_id}", status_code=204)
def delete_expense(expense_id: int, db: Session = Depends(get_db)) -> Response:
    expense_service.delete_expense(db, expense_id)
    return Response(status_code=204)
