from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from schemas.user import UserResponse
from schemas.pagination import PaginatedResponse
from database import get_DB
from service.service import get_users
from dependencies.dep import get_current_user, require_admin
from models.user import User

router = APIRouter(prefix='/users', tags=["User"])


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user:User=Depends(get_current_user)):
    return current_user


@router.get("/", response_model=PaginatedResponse[UserResponse])
def handle_read_user(
    page: int = 1,
    size: int = 10,
    sort_by: str = "id",
    order: str = "asc",
    search: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_DB),
    role: User = Depends(require_admin)
):
    return get_users(
        db=db,
        page=page,
        size=size,
        sort_by=sort_by,
        order=order,
        search=search,
        is_active=is_active
    )

