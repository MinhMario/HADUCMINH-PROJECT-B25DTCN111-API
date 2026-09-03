from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_DB
from app.dependencies.deps import get_current_user
from app.schemas.campaign_task import CampaignTaskCreate, CampaignTaskResponse, CampaignTaskUpdate
from app.schemas.task_comment import TaskCommentCreate, TaskCommentResponse
from app.schemas.pagination import PaginatedResponse
from app.models.user import User
from app.services.service import (
    add_campaign_task, get_campaign_tasks, get_campaign_task_by_id,
    update_campaign_task, delete_campaign_task,
    create_task_comment, get_task_comments,
)

router = APIRouter(tags=["Campaign Task"])


@router.post("/campaigns/{campaign_id}/campaign-tasks",
             response_model=CampaignTaskResponse, status_code=status.HTTP_201_CREATED)
def handle_create_task(campaign_id: int, task: CampaignTaskCreate,
                        db: Session = Depends(get_DB), current_user: User = Depends(get_current_user)):
    return add_campaign_task(campaign_id=campaign_id, db=db, user_id=current_user.id, payload=task)


@router.get("/campaigns/{campaign_id}/campaign-tasks",
            response_model=PaginatedResponse[CampaignTaskResponse], status_code=status.HTTP_200_OK)
def handle_get_tasks(campaign_id: int, page: int = 1, size: int = 10,
                      sort_by: str = "created_at", order: str = "desc",
                      status: str | None = None, priority: str | None = None,
                      assignee_id: int | None = None, search: str | None = None,
                      db: Session = Depends(get_DB), current_user: User = Depends(get_current_user)):
    return get_campaign_tasks(campaign_id=campaign_id, db=db, user_id=current_user.id,
                               page=page, size=size, sort_by=sort_by, order=order,
                               status=status, priority=priority, assignee_id=assignee_id, search=search)


@router.get("/campaign-tasks/{id}", response_model=CampaignTaskResponse, status_code=status.HTTP_200_OK)
def handle_get_task(id: int, db: Session = Depends(get_DB), current_user: User = Depends(get_current_user)):
    return get_campaign_task_by_id(task_id=id, user_id=current_user.id, db=db)


@router.patch("/campaign-tasks/{id}", response_model=CampaignTaskResponse, status_code=status.HTTP_200_OK)
def handle_patch_task(id: int, payload: CampaignTaskUpdate,
                       db: Session = Depends(get_DB), current_user: User = Depends(get_current_user)):
    return update_campaign_task(task_id=id, db=db, user_id=current_user.id, payload=payload)


@router.delete("/campaign-tasks/{id}", status_code=status.HTTP_200_OK)
def handle_delete_task(id: int, db: Session = Depends(get_DB), current_user: User = Depends(get_current_user)):
    return delete_campaign_task(task_id=id, db=db, user_id=current_user.id)


@router.post("/campaign-tasks/{id}/comments",
             response_model=TaskCommentResponse, status_code=status.HTTP_201_CREATED)
def handle_create_comment(id: int, payload: TaskCommentCreate,
                           db: Session = Depends(get_DB), current_user: User = Depends(get_current_user)):
    return create_task_comment(task_id=id, user_id=current_user.id, payload=payload, db=db)


@router.get("/campaign-tasks/{id}/comments",
            response_model=PaginatedResponse[TaskCommentResponse], status_code=status.HTTP_200_OK)
def handle_get_comments(id: int, page: int = 1, size: int = 10,
                         sort_by: str = "created_at", order: str = "asc",
                         db: Session = Depends(get_DB), current_user: User = Depends(get_current_user)):
    return get_task_comments(task_id=id, user_id=current_user.id, db=db,
                              page=page, size=size, sort_by=sort_by, order=order)
