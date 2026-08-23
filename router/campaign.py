from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, status

from database import get_DB
from schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
    CampaignPatch,
    CampaignMemberResponse,
    CampaignMemberAdd,
)
from schemas.campaign_task import CampaignTaskCreate,CampaignTaskResponse,CampaignTaskUpdate
from dependencies.dep import get_current_user
from models.user import User
from service.service import *


router = APIRouter(prefix="/campaigns", tags=["Campaign"])


@router.post("/", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def handle_create_campaign(
    campaign: CampaignCreate,
    db: Session = Depends(get_DB),
    current_user: User = Depends(get_current_user)
):
    return create_campaign(campaign_in=campaign, owner_id=current_user.id, db=db)


@router.get("/", response_model=list[CampaignResponse])
def handle_list_campaigns(
    search: str | None = None,
    db: Session = Depends(get_DB),
    current_user: User = Depends(get_current_user)
):
    return list_campaigns(db=db, user_id=current_user.id, search=search)


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_DB),
    user: User = Depends(get_current_user)
):
    return read_campaigns(campaign_id, db, user.id)


@router.put("/{campaign_id}", response_model=CampaignResponse)
def handle_update_campaign(
    campaign_id: int,
    campaign_update: CampaignUpdate,
    db: Session = Depends(get_DB),
    current_user: User = Depends(get_current_user)
):
    return update_campaign(campaign_id=campaign_id, db=db, owner_id=current_user.id, payload=campaign_update)


@router.patch("/{campaign_id}", response_model=CampaignResponse)
def handle_patch_campaign(
    campaign_id: int,
    campaign_patch: CampaignPatch,
    db: Session = Depends(get_DB),
    current_user: User = Depends(get_current_user)
):
    return update_campaign(campaign_id=campaign_id, db=db, owner_id=current_user.id, payload=campaign_patch)



@router.delete("/{campaign_id}", response_model=CampaignResponse)
def handle_delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_DB),
    current_user: User = Depends(get_current_user)
):
    return delete_campaign(campaign_id=campaign_id, db=db, owner_id=current_user.id)


@router.post("/{campaign_id}/members", response_model=CampaignMemberResponse, status_code=status.HTTP_201_CREATED)
def handle_add_campaign_member(
    campaign_id: int,
    payload: CampaignMemberAdd,
    db: Session = Depends(get_DB),
    current_user: User = Depends(get_current_user)
):
    return add_campaign_member(
        campaign_id=campaign_id,
        new_user_id=payload.user_id,
        db=db,
        owner_id=current_user.id
    )


@router.get("/{campaign_id}/members", response_model=list[CampaignMemberResponse])
def handle_get_campaign_members(
    campaign_id: int,
    db: Session = Depends(get_DB),
    current_user: User = Depends(get_current_user)
):
    return get_campaign_members(campaign_id=campaign_id, db=db, user_id=current_user.id)


@router.delete("/{campaign_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def handle_delete_campaign_member(
    campaign_id: int,
    user_id: int,
    db: Session = Depends(get_DB),
    current_user: User = Depends(get_current_user)
):
    return  delete_campaign_member(
        campaign_id=campaign_id,
        db=db,
        user_id=user_id,
        owner_id=current_user.id
    )
@router.post("/{campaign_id}/campaign-tasks", status_code=status.HTTP_201_CREATED,response_model=CampaignTaskResponse)
def handle_create_campaign_task(task:CampaignTaskCreate,campaign_id:int,user_id:int,db:Session=Depends(get_DB)):
    return add_campaign_task(campaign_id,db,user_id,task)
@router.get("/{campaign_id}/campaign-tasks",status_code=status.HTTP_200_OK,response_model=CampaignTaskResponse)
def handle_get_campaign_tasks(campaign_id:int,user_id:int,db:Session=Depends(get_DB)):
    return get_campaign_tasks(campaign_id,db,user_id)