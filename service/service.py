from sqlalchemy.orm import Session
from sqlalchemy import or_

from core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from core.security import hash_pass, verify_pass
from datetime import datetime
from schemas.user import UserCreate, UserLogin
from schemas.campaign import CampaignCreate, CampaignUpdate, CampaignPatch
from schemas.campaign_task import CampaignTaskCreate
from models.user import User
from models.campaign import Campaign, CampaignMember
from models.campaign_task import CampaignTask


def create_user(user: UserCreate, db: Session):
    duplicate_email = db.query(User).filter(User.email == user.email).first()
    if duplicate_email:
        raise BadRequestException("Email đã bị trùng")

    new_user = User(
        full_name=user.full_name,
        email=user.email,
        password_hash=hash_pass(user.password),
        role="USER",
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def authenticate_user(credentials: UserLogin, db: Session):
    user = db.query(User).filter(User.email == credentials.email).first()

    if user is None:
        raise BadRequestException("Email hoặc mật khẩu không đúng")

    if not verify_pass(credentials.password, user.password_hash):
        raise BadRequestException("Email hoặc mật khẩu không đúng")

    if not user.is_active:
        raise ForbiddenException("Tài khoản đã bị vô hiệu hóa")

    return user


def get_users(db: Session, search: str | None = None, is_active: bool | None = None):
    query = db.query(User)

    if search:
        search = search.strip()
        query = query.filter(
            (User.full_name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%"))
        )

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    return query.all()


def create_campaign(campaign_in: CampaignCreate, owner_id: int, db: Session) -> Campaign:
    new_campaign = Campaign(
        name=campaign_in.name,
        description=campaign_in.description,
        owner_id=owner_id
    )
    db.add(new_campaign)
    db.commit()
    db.refresh(new_campaign)

    new_member = CampaignMember(
        campaign_id=new_campaign.id,
        user_id=owner_id,
        role="OWNER"
    )
    db.add(new_member)
    db.commit()

    return new_campaign


def list_campaigns(db: Session, user_id: int, search: str | None = None):
    member_campaign_ids = (
        db.query(CampaignMember.campaign_id)
        .filter(CampaignMember.user_id == user_id)
    )

    query = db.query(Campaign).filter(
        Campaign.is_deleted == False,
        or_(
            Campaign.owner_id == user_id,
            Campaign.id.in_(member_campaign_ids)
        )
    )

    if search:
        search = search.strip()
        query = query.filter(Campaign.name.ilike(f"%{search}%"))

    return query.all()


def read_campaigns(campaign_id: int, db: Session, user_id: int) -> Campaign:
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.is_deleted == False
    ).first()

    if not campaign:
        raise NotFoundException("Campaign không tồn tại")

    is_member = (
        db.query(CampaignMember)
        .filter(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user_id,
        )
        .first()
    )

    if not is_member:
        raise ForbiddenException("Bạn không phải thành viên của campaign này")

    return campaign


def update_campaign(campaign_id: int, db: Session, owner_id: int, payload: CampaignUpdate | CampaignPatch) -> Campaign:
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.is_deleted == False
    ).first()

    if not campaign:
        raise NotFoundException("Campaign không tồn tại")

    if campaign.owner_id != owner_id:
        raise ForbiddenException("Bạn không phải chủ của campaign này")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(campaign, field, value)

    db.commit()
    db.refresh(campaign)
    return campaign


def delete_campaign(campaign_id: int, db: Session, owner_id: int):
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.is_deleted == False
    ).first()

    if not campaign:
        raise NotFoundException("Campaign không tồn tại")

    if campaign.owner_id != owner_id:
        raise ForbiddenException("Bạn không phải chủ của campaign này")

    campaign.is_deleted = True
    campaign.deleted_at = datetime.utcnow()
    db.commit()
    return campaign


def add_campaign_member(campaign_id: int, new_user_id: int, db: Session, owner_id: int):
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.is_deleted == False
    ).first()

    if not campaign:
        raise NotFoundException("Campaign không tồn tại")

    if campaign.owner_id != owner_id:
        raise ForbiddenException("Bạn không phải chủ của campaign này")

    user = db.query(User).filter(User.id == new_user_id).first()
    if not user:
        raise NotFoundException("User không tồn tại")

    existing = (
        db.query(CampaignMember)
        .filter(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == new_user_id,
        )
        .first()
    )
    if existing:
        raise BadRequestException("User đã là thành viên của campaign này")

    new_member = CampaignMember(
        campaign_id=campaign_id,
        user_id=new_user_id,
        role="MEMBER"
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    return new_member


def delete_campaign_member(campaign_id: int, db: Session, user_id: int, owner_id: int):
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.is_deleted == False
    ).first()

    if not campaign:
        raise NotFoundException("Campaign không tồn tại")

    if campaign.owner_id != owner_id:
        raise ForbiddenException("Bạn không phải chủ của campaign này")

    member = (
        db.query(CampaignMember)
        .filter(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user_id,
        )
        .first()
    )
    if not member:
        raise NotFoundException("Thành viên không tồn tại trong campaign này")

    if user_id == campaign.owner_id:
        raise BadRequestException("Không thể xóa owner của campaign")

    db.delete(member)
    db.commit()
    return member


def get_campaign_members(campaign_id: int, db: Session, user_id: int):
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.is_deleted == False
    ).first()

    if not campaign:
        raise NotFoundException("Campaign không tồn tại")

    is_member = (
        db.query(CampaignMember)
        .filter(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user_id,
        )
        .first()
    )
    if not is_member:
        raise ForbiddenException("Bạn không phải thành viên của campaign này")

    return (
        db.query(CampaignMember)
        .filter(CampaignMember.campaign_id == campaign_id)
        .all()
    )
    
def add_campaign_task(campaign_id: int, db: Session, user_id: int, payload: CampaignTaskCreate) -> CampaignTask:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.is_deleted == False).first()
    if not campaign:
        raise NotFoundException('Không tìm thấy chiến dịch')
    is_member = db.query(CampaignMember).filter(CampaignMember.user_id == user_id, CampaignMember.campaign_id == campaign_id).first()
    if not is_member:
        raise ForbiddenException('Bạn không phải thành viên của chiến dịch này')
    new_task = CampaignTask(  
        campaign_id=campaign_id,
        title=payload.title,
        description=payload.description,
        assignee_id=payload.assignee_id,
        status=payload.status or "TODO",
        due_date=payload.due_date,
        priority=payload.priority or "MEDIUM"
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


def get_campaign_tasks(campaign_id: int, db: Session, user_id: int) -> list[CampaignTask]:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.is_deleted == False).first()
    if not campaign:
        raise NotFoundException('Không tìm thấy chiến dịch')
    is_member = db.query(CampaignMember).filter(CampaignMember.user_id == user_id, CampaignMember.campaign_id == campaign_id).first()
    if not is_member:
        raise ForbiddenException('Bạn không phải thành viên của chiến dịch này')
    return db.query(CampaignTask).filter(CampaignTask.campaign_id == campaign_id).all()


def delete_campaign_task(task_id: int, db: Session, user_id: int):
    task = db.query(CampaignTask).filter(CampaignTask.id == task_id).first()
    if not task:
        raise NotFoundException('Không tìm thấy đầu việc')
    campaign = db.query(Campaign).filter(Campaign.id == task.campaign_id, Campaign.is_deleted == False).first()
    if not campaign:
        raise NotFoundException('Không tìm thấy chiến dịch')
    is_member = db.query(CampaignMember).filter(CampaignMember.user_id == user_id, CampaignMember.campaign_id == task.campaign_id).first()
    if not is_member:
        raise ForbiddenException('Bạn không phải thành viên của chiến dịch này')
    db.delete(task)
    db.commit()
    return task

