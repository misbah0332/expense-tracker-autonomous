"""Spending totals and category breakdowns."""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.schemas import SummaryRead
from app.services.dates import ensure_date_order
from app.services.summary import spending_summary

router = APIRouter(
    prefix="/summary",
    tags=["summary"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=SummaryRead)
def summary(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
) -> dict:
    ensure_date_order(date_from, date_to)
    return spending_summary(db, date_from=date_from, date_to=date_to)
