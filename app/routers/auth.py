from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_DB
from app.core.security import create_access_token, create_refresh_token, decode_access_token
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token, RefreshRequest
from app.services.service import create_user, authenticate_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def handle_register(user: UserCreate, db: Session = Depends(get_DB)):
    return create_user(user, db)


@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
def handle_login(credentials: UserLogin, db: Session = Depends(get_DB)):
    user = authenticate_user(credentials, db)
    return Token(
        access_token=create_access_token(email=user.email, user_id=user.id),
        refresh_token=create_refresh_token(email=user.email, user_id=user.id)
    )


@router.post("/refresh", response_model=Token, status_code=status.HTTP_200_OK)
def handle_refresh(payload: RefreshRequest, db: Session = Depends(get_DB)):
    token_data = decode_access_token(payload.refresh_token)
    if token_data.get("type") != "refresh":
        raise UnauthorizedException("Token không đúng loại (yêu cầu refresh token)")
    user_id = token_data.get("user_id")
    email = token_data.get("sub")
    if not user_id or not email:
        raise UnauthorizedException("Token không hợp lệ")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UnauthorizedException("Người dùng không tồn tại")
    if not user.is_active:
        raise ForbiddenException("Tài khoản đã bị vô hiệu hóa")
    return Token(
        access_token=create_access_token(email=user.email, user_id=user.id),
        refresh_token=create_refresh_token(email=user.email, user_id=user.id)
    )
