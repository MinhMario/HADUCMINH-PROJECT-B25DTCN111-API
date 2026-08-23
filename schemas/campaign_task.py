from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class CampaignTaskBase(BaseModel):
    title: str
    description: str 
    assignee_id: int 
    status: str = "TODO"          # TODO / IN_PROGRESS / DONE
    priority: str = "MEDIUM"      # LOW / MEDIUM / HIGH
    due_date: datetime 


class CampaignTaskCreate(CampaignTaskBase):
    pass


class CampaignTaskUpdate(BaseModel):
    title: str 
    description: str 
    assignee_id: int 
    status: str 
    priority: str 
    due_date: datetime 


class CampaignTaskResponse(CampaignTaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    created_at: datetime
