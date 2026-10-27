"""Category queries. Predefined rows are seeded and cannot be removed through the API."""

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.models import Category, Expense


def list_categories(db: Session) -> list[Category]:
    return (
        db.query(Category)
        .order_by(Category.is_predefined.desc(), Category.name.asc())
        .all()
    )


def create_category(db: Session, name: str) -> Category:
    existing = (
        db.query(Category).filter(func.lower(Category.name) == name.lower()).one_or_none()
    )
    if existing is not None:
        raise ConflictError("Category already exists")

    category = Category(name=name, is_predefined=False)
    db.add(category)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Category already exists") from None
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int) -> None:
    category = db.get(Category, category_id)
    if category is None:
        raise NotFoundError("Category not found")
    if category.is_predefined:
        raise ForbiddenError("Predefined categories cannot be deleted")
    in_use = db.query(Expense.id).filter(Expense.category_id == category_id).first()
    if in_use is not None:
        raise ConflictError("Category is used by one or more expenses")

    db.delete(category)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Category is used by one or more expenses") from None


def require_category(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise BadRequestError("category_id does not match an existing category")
    return category
