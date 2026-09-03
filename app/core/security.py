import bcrypt
from datetime import datetime, timezone, timedelta
from jose import ExpiredSignatureError, JWTError, jwt
from app.core.config import SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_TIME, REFRESH_TOKEN_TIME
from app.core.exceptions import UnauthorizedException


def hash_pass(password: str) -> str:
    pass_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pass_bytes, salt)
    return hashed.decode("utf-8")


def verify_pass(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def create_access_token(email: str, user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_TIME)
    payload = {"sub": email, "user_id": user_id, "exp": expire, "type": "access"}
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(email: str, user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_TIME)
    payload = {"sub": email, "user_id": user_id, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except ExpiredSignatureError:
        raise UnauthorizedException("Token đã hết hạn, vui lòng đăng nhập lại")
    except JWTError:
        raise UnauthorizedException("Token không hợp lệ")
