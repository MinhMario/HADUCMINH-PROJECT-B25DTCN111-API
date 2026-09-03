from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_DB
from app.dependencies.deps import get_current_user
from app.schemas.campaign import (
    CampaignCreate, CampaignResponse, CampaignUpdate, CampaignPatch,
    CampaignMemberResponse, CampaignMemberAdd,
)
from app.schemas.pagination import PaginatedResponse
from app.models.user import User
from app.services.service import (
    create_campaign, list_campaigns, read_campaigns,
    update_campaign, delete_campaign,
    add_campaign_member, get_campaign_members, delete_campaign_member,
)

router = APIRouter(prefix="/campaigns", tags=["Campaign"])


@router.post("/", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def handle_create_campaign(campaign: CampaignCreate, db: Session = Depends(get_DB),
                            current_user: User = Depends(get_current_user)):
    return create_campaign(campaign_in=campaign, owner_id=current_user.id, db=db)


@router.get("/", response_model=PaginatedResponse[CampaignResponse], status_code=status.HTTP_200_OK)
def handle_list_campaigns(page: int = 1, size: int = 10, search: str | None = None,
                           db: Session = Depends(get_DB), current_user: User = Depends(get_current_user)):
    return list_campaigns(db=db, user_id=current_user.id, page=page, size=size, search=search)


@router.get("/{campaign_id}", response_model=CampaignResponse, status_code=status.HTTP_200_OK)
def handle_get_campaign(campaign_id: int, db: Session = Depends(get_DB),
                         user: User = Depends(get_current_user)):
    return read_campaigns(campaign_id, db, user.id)


@router.put("/{campaign_id}", response_model=CampaignResponse, status_code=status.HTTP_200_OK)
def handle_update_campaign(campaign_id: int, payload: CampaignUpdate,
                            db: Session = Depends(get_DB), current_user: User = Depends(get_current_user)):
    return update_campaign(campaign_id=campaign_id, db=db, owner_id=current_user.id, payload=payload)


@router.patch("/{campaign_id}", response_model=CampaignResponse, status_code=status.HTTP_200_OK)
def handle_patch_campaign(campaign_id: int, payload: CampaignPatch,
                           db: Session = Depends(get_DB), current_user: User = Depends(get_current_user)):
    return update_campaign(campaign_id=campaign_id, db=db, owner_id=current_user.id, payload=payload)


@router.delete("/{campaign_id}", response_model=CampaignResponse, status_code=status.HTTP_200_OK)
def handle_delete_campaign(campaign_id: int, db: Session = Depends(get_DB),
                            current_user: User = Depends(get_current_user)):
    return delete_campaign(campaign_id=campaign_id, db=db, owner_id=current_user.id)


@router.post("/{campaign_id}/members", response_model=CampaignMemberResponse, status_code=status.HTTP_201_CREATED)
def handle_add_member(campaign_id: int, payload: CampaignMemberAdd,
                       db: Session = Depends(get_DB), current_user: User = Depends(get_current_user)):
    return add_campaign_member(campaign_id=campaign_id, new_user_id=payload.user_id,
                                db=db, owner_id=current_user.id)


@router.get("/{campaign_id}/members", response_model=list[CampaignMemberResponse], status_code=status.HTTP_200_OK)
def handle_get_members(campaign_id: int, db: Session = Depends(get_DB),
                        current_user: User = Depends(get_current_user)):
    return get_campaign_members(campaign_id=campaign_id, db=db, user_id=current_user.id)


@router.delete("/{campaign_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def handle_delete_member(campaign_id: int, user_id: int,
                          db: Session = Depends(get_DB), current_user: User = Depends(get_current_user)):
    delete_campaign_member(campaign_id=campaign_id, db=db, user_id=user_id, owner_id=current_user.id)
    return None
