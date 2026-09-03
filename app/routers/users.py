from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_DB
from app.dependencies.deps import get_current_user, require_admin
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.pagination import PaginatedResponse
from app.models.user import User
from app.services.service import get_users

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def handle_get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/", response_model=PaginatedResponse[UserResponse], status_code=status.HTTP_200_OK)
def handle_get_users(
    page: int = 1, size: int = 10, sort_by: str = "id", order: str = "asc",
    search: str | None = None, is_active: bool | None = None,
    db: Session = Depends(get_DB),
    role: User = Depends(require_admin)
):
    return get_users(db=db, page=page, size=size, sort_by=sort_by, order=order,
                     search=search, is_active=is_active)
