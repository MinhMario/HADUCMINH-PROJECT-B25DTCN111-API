from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from schemas.user import *
from database import *
from service.service import *
from core.security import create_access_token, create_refresh_token, decode_access_token
from core.exceptions import UnauthorizedException, ForbiddenException
from models.user import User

router = APIRouter(prefix='/auth',tags=["Authentication"])

@router.post('/register',response_model=UserResponse)
def handle_create_user(user:UserCreate,db:Session=Depends(get_DB)):
    new_user=create_user(user,db)
    return new_user


@router.post('/login', response_model=Token)
def handle_login(credentials: UserLogin, db: Session = Depends(get_DB)):
    user = authenticate_user(credentials, db)
    access_token = create_access_token(
        email=user.email,
        user_id=user.id
    )
    refresh_token = create_refresh_token(
        email=user.email,
        user_id=user.id
    )
    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post('/refresh', response_model=Token)
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

    new_access = create_access_token(email=user.email, user_id=user.id)
    new_refresh = create_refresh_token(email=user.email, user_id=user.id)

    return Token(
        access_token=new_access,
        refresh_token=new_refresh
    )