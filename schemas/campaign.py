from datetime import datetime

from pydantic import BaseModel, ConfigDict,Field


class CampaignBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str


class CampaignUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str


class CampaignPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None



class CampaignCreate(CampaignBase):
    pass




class CampaignResponse(CampaignBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    created_at: datetime


class CampaignMemberBase(BaseModel):
    user_id: int
    role: str  # OWNER / MEMBER


class CampaignMemberAdd(BaseModel):
    user_id: int



class CampaignMemberCreate(CampaignMemberBase):
    pass


class CampaignMemberUpdate(BaseModel):
    role: str 


class CampaignMemberResponse(CampaignMemberBase):
    model_config = ConfigDict(from_attributes=True)

    campaign_id: int
    joined_at: datetime
