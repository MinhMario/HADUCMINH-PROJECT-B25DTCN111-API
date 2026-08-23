from sqlalchemy.orm import Session
from schemas import *
from fastapi import FastAPI
from router.health import router
from router.auth import router as auth_router
from router.user import router as user_router
from router.campaign import router as campaign_router

from database import *
from models import *
from core.exceptions import (
    BadRequestException,
    UnauthorizedException,
    NotFoundException,
    ForbiddenException,
    exception_handler
)

Base.metadata.create_all(bind=engine)
app=FastAPI()
app.include_router(router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(campaign_router)
app.add_exception_handler(BadRequestException, exception_handler)
app.add_exception_handler(UnauthorizedException, exception_handler)
app.add_exception_handler(NotFoundException, exception_handler)
app.add_exception_handler(ForbiddenException, exception_handler)

