from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CampaignTaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    due_date: datetime | None = None
    priority: str = "MEDIUM"
    assignee_id: int | None = None


class CampaignTaskCreate(CampaignTaskBase):
    status: str = "TODO"


class CampaignTaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    assignee_id: int | None = None
    status: str | None = None
    priority: str | None = None
    due_date: datetime | None = None


class CampaignTaskResponse(CampaignTaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    assignee_id: int | None = None
    status: str = "TODO"
    created_at: datetime

