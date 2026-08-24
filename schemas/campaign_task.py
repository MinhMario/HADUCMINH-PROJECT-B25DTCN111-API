from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class CampaignTaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None 
    assignee_id: int | None = None 
    status: str = "TODO"          # TODO / IN_PROGRESS / DONE
    priority: str = "MEDIUM"      # LOW / MEDIUM / HIGH
    due_date: datetime | None = None 


class CampaignTaskCreate(CampaignTaskBase):
    pass


class CampaignTaskUpdate(BaseModel):
    title: str | None = None 
    description: str | None = None 
    assignee_id: int | None = None 
    status: str | None = None 
    priority: str | None = None 
    due_date: datetime | None = None 


class CampaignTaskResponse(CampaignTaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    created_at: datetime
