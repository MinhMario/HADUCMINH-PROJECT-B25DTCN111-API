from fastapi import FastAPI
from app.db.database import engine, Base
from app.core.exceptions import (
    BadRequestException, UnauthorizedException,
    NotFoundException, ForbiddenException, exception_handler
)
from app.routers import auth, users, campaign, campaign_task

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Campaign Management API")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(campaign.router)
app.include_router(campaign_task.router)

app.add_exception_handler(BadRequestException, exception_handler)
app.add_exception_handler(UnauthorizedException, exception_handler)
app.add_exception_handler(NotFoundException, exception_handler)
app.add_exception_handler(ForbiddenException, exception_handler)
