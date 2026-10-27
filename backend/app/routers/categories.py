"""List, create, and delete categories."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.schemas import CategoryCreate, CategoryRead
from app.services import categories as category_service

router = APIRouter(
    prefix="/categories",
    tags=["categories"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[CategoryRead])
def list_categories(db: Session = Depends(get_db)) -> list:
    return category_service.list_categories(db)


@router.post("", response_model=CategoryRead, status_code=201)
def create_category(body: CategoryCreate, db: Session = Depends(get_db)) -> object:
    return category_service.create_category(db, body.name)


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)) -> Response:
    category_service.delete_category(db, category_id)
    return Response(status_code=204)
