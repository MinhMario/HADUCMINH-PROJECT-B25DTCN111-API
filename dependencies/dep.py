
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy.orm import Session

from core.exceptions import (
    UnauthorizedException,
    ForbiddenException
)
from database import get_DB
from models.user import User
from core.security import decode_access_token
http_bearer = HTTPBearer(auto_error=False)
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
    db: Session = Depends(get_DB)
) -> User:

    if credentials is None:
        raise UnauthorizedException("Thiếu Authorization header")

    payload = decode_access_token(credentials.credentials)

    if payload.get("type") != "access":
        raise UnauthorizedException("Token không đúng loại (yêu cầu access token)")

    user_id: int | None = payload.get("user_id")
    if user_id is None:
        raise UnauthorizedException("Token không chứa thông tin người dùng")

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise UnauthorizedException("Người dùng không tồn tại")

    if not user.is_active:
        raise ForbiddenException("Tài khoản đã bị vô hiệu hóa")

    return user


class RoleChecker:
    # constructor
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        current_user: User = Depends(get_current_user)
    ) -> User:
        if current_user.role not in self.allowed_roles:
            raise ForbiddenException(
                f"Bạn không có quyền truy cập. "
                f"Yêu cầu role: {', '.join(self.allowed_roles)}"
            )
        return current_user

require_user  = RoleChecker(["USER", "ADMIN"])   # cả hai role đều vào được
require_admin = RoleChecker(["ADMIN"])            # chỉ ADMIN