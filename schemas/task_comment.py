from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from schemas.user import UserResponse


class TaskCommentCreate(BaseModel):
    content: str = Field(min_length=1, description="Nội dung trao đổi / bình luận")


class TaskCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    user_id: int
    content: str
    created_at: datetime
    user: UserResponse | None = None
