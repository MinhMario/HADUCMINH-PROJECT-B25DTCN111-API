from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from schemas.user import UserResponse
from database import get_DB
from service.service import get_users
from dependencies.dep import get_current_user, require_admin
from models.user import User

router = APIRouter(prefix='/users', tags=["User"])


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user:User=Depends(get_current_user)):
    return current_user


@router.get("/", response_model=list[UserResponse])
def handle_read_user(
    db: Session = Depends(get_DB),
    search: str | None = None,
    is_active: bool | None = None,
    role: User = Depends(require_admin)
):
    return get_users(db=db, search=search, is_active=is_active)
