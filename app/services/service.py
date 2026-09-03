import math
from datetime import datetime, timezone,timedelta
from sqlalchemy.orm import Session, Query
from sqlalchemy import or_

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.core.security import hash_pass, verify_pass
from app.schemas.user import UserCreate, UserLogin
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignPatch
from app.schemas.campaign_task import CampaignTaskCreate, CampaignTaskUpdate
from app.schemas.task_comment import TaskCommentCreate
from app.models.user import User
from app.models.campaign import Campaign, CampaignMember
from app.models.campaign_task import CampaignTask
from app.models.task_comment import TaskComment


VALID_TASK_STATUSES = {"TODO", "IN_PROGRESS", "DONE"}
VALID_TASK_PRIORITIES = {"LOW", "MEDIUM", "HIGH"}


def _as_utc(dt: datetime) -> datetime:
    """Ép datetime naive về UTC-aware nếu cần."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def paginate(query: Query, page: int = 1, size: int = 10) -> dict:
    page = max(page or 1, 1)
    size = max(size or 10, 1)
    total = query.count()
    total_pages = math.ceil(total / size) if size > 0 else 0
    items = query.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "total_pages": total_pages, "items": items}


def apply_sorting(query: Query, sort_by: str = "created_at", order: str = "desc") -> Query:
    col = CampaignTask.due_date if sort_by == "due_date" else CampaignTask.created_at
    is_desc = (order or "desc").lower() == "desc"
    return query.order_by(col.desc() if is_desc else col.asc())


# ── USER ──────────────────────────────────────────────────────────────────────

def create_user(user: UserCreate, db: Session):
    if not user.full_name or not user.full_name.strip():
        raise BadRequestException("Họ và tên không được để trống")
    if db.query(User).filter(User.email == user.email).first():
        raise BadRequestException("Email đã bị trùng")
    new_user = User(
        full_name=user.full_name.strip(),
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
    if user is None or not verify_pass(credentials.password, user.password_hash):
        raise BadRequestException("Email hoặc mật khẩu không đúng")
    if not user.is_active:
        raise ForbiddenException("Tài khoản đã bị vô hiệu hóa")
    return user


def get_users(db: Session, page: int = 1, size: int = 10, sort_by: str = "id",
              order: str = "asc", search: str | None = None, is_active: bool | None = None):
    query = db.query(User)
    if search:
        search = search.strip()
        query = query.filter(
            (User.full_name.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
        )
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    _sort_map = {"id": User.id, "full_name": User.full_name, "email": User.email, "role": User.role}
    col = _sort_map.get(sort_by, User.id)
    is_desc = (order or "asc").lower() == "desc"
    query = query.order_by(col.desc() if is_desc else col.asc())
    return paginate(query, page=page, size=size)


# ── CAMPAIGN ──────────────────────────────────────────────────────────────────

def create_campaign(campaign_in: CampaignCreate, owner_id: int, db: Session) -> Campaign:
    if not campaign_in.name or not campaign_in.name.strip():
        raise BadRequestException("Tên chiến dịch không được để trống")
    new_campaign = Campaign(name=campaign_in.name.strip(), description=campaign_in.description, owner_id=owner_id)
    db.add(new_campaign)
    db.commit()
    db.refresh(new_campaign)
    db.add(CampaignMember(campaign_id=new_campaign.id, user_id=owner_id, role="OWNER"))
    db.commit()
    return new_campaign


def list_campaigns(db: Session, user_id: int, page: int = 1, size: int = 10, search: str | None = None):
    member_ids = db.query(CampaignMember.campaign_id).filter(CampaignMember.user_id == user_id)
    query = db.query(Campaign).filter(
        Campaign.is_deleted == False,
        or_(Campaign.owner_id == user_id, Campaign.id.in_(member_ids))
    )
    if search:
        query = query.filter(Campaign.name.ilike(f"%{search.strip()}%"))
    query = query.order_by(Campaign.created_at.desc())
    return paginate(query, page=page, size=size)


def read_campaigns(campaign_id: int, db: Session, user_id: int) -> Campaign:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.is_deleted == False).first()
    if not campaign:
        raise NotFoundException("Campaign không tồn tại")
    is_member = db.query(CampaignMember).filter(
        CampaignMember.campaign_id == campaign_id, CampaignMember.user_id == user_id
    ).first()
    if not is_member and campaign.owner_id != user_id:
        raise ForbiddenException("Bạn không phải thành viên của campaign này")
    return campaign


def update_campaign(campaign_id: int, db: Session, owner_id: int,
                    payload: CampaignUpdate | CampaignPatch) -> Campaign:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.is_deleted == False).first()
    if not campaign:
        raise NotFoundException("Campaign không tồn tại")
    if campaign.owner_id != owner_id:
        raise ForbiddenException("Bạn không phải chủ của campaign này")
    update_data = payload.model_dump(exclude_unset=True)
    if "name" in update_data:
        if update_data["name"] is None or not str(update_data["name"]).strip():
            raise BadRequestException("Tên chiến dịch không được để trống")
        update_data["name"] = str(update_data["name"]).strip()
    for field, value in update_data.items():
        setattr(campaign, field, value)
    db.commit()
    db.refresh(campaign)
    return campaign


def delete_campaign(campaign_id: int, db: Session, owner_id: int):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.is_deleted == False).first()
    if not campaign:
        raise NotFoundException("Campaign không tồn tại")
    if campaign.owner_id != owner_id:
        raise ForbiddenException("Bạn không phải chủ của campaign này")
    campaign.is_deleted = True
    campaign.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return campaign


def add_campaign_member(campaign_id: int, new_user_id: int, db: Session, owner_id: int):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.is_deleted == False).first()
    if not campaign:
        raise NotFoundException("Campaign không tồn tại")
    if campaign.owner_id != owner_id:
        raise ForbiddenException("Bạn không phải chủ của campaign này")
    if not db.query(User).filter(User.id == new_user_id).first():
        raise NotFoundException("User không tồn tại")
    existing = db.query(CampaignMember).filter(
        CampaignMember.campaign_id == campaign_id, CampaignMember.user_id == new_user_id
    ).first()
    if existing:
        raise BadRequestException("User đã là thành viên của campaign này")
    new_member = CampaignMember(campaign_id=campaign_id, user_id=new_user_id, role="MEMBER")
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    return new_member


def delete_campaign_member(campaign_id: int, db: Session, user_id: int, owner_id: int):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.is_deleted == False).first()
    if not campaign:
        raise NotFoundException("Campaign không tồn tại")
    if campaign.owner_id != owner_id:
        raise ForbiddenException("Bạn không phải chủ của campaign này")
    member = db.query(CampaignMember).filter(
        CampaignMember.campaign_id == campaign_id, CampaignMember.user_id == user_id
    ).first()
    if not member:
        raise NotFoundException("Thành viên không tồn tại trong campaign này")
    if user_id == campaign.owner_id:
        raise BadRequestException("Không thể xóa owner của campaign")
    db.delete(member)
    db.commit()
    return member


def get_campaign_members(campaign_id: int, db: Session, user_id: int):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.is_deleted == False).first()
    if not campaign:
        raise NotFoundException("Campaign không tồn tại")
    is_member = db.query(CampaignMember).filter(
        CampaignMember.campaign_id == campaign_id, CampaignMember.user_id == user_id
    ).first()
    if not is_member and campaign.owner_id != user_id:
        raise ForbiddenException("Bạn không phải thành viên của campaign này")
    return db.query(CampaignMember).filter(CampaignMember.campaign_id == campaign_id).all()


# ── CAMPAIGN TASK ─────────────────────────────────────────────────────────────

def add_campaign_task(campaign_id: int, db: Session, user_id: int, payload: CampaignTaskCreate) -> CampaignTask:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.is_deleted == False).first()
    if not campaign:
        raise NotFoundException("Không tìm thấy chiến dịch")
    is_member = db.query(CampaignMember).filter(
        CampaignMember.user_id == user_id, CampaignMember.campaign_id == campaign_id
    ).first()
    if not is_member and campaign.owner_id != user_id:
        raise ForbiddenException("Bạn không phải thành viên của chiến dịch này")
    if not payload.title or not payload.title.strip():
        raise BadRequestException("Tiêu đề công việc không được để trống")
    if payload.status and payload.status.upper() not in VALID_TASK_STATUSES:
        raise BadRequestException("Trạng thái không hợp lệ (chỉ chấp nhận TODO, IN_PROGRESS, DONE)")
    if payload.priority and payload.priority.upper() not in VALID_TASK_PRIORITIES:
        raise BadRequestException("Độ ưu tiên không hợp lệ (chỉ chấp nhận LOW, MEDIUM, HIGH)")
    if payload.due_date is not None and _as_utc(payload.due_date) < datetime.now(timezone.utc) + timedelta(hours=1):
        raise BadRequestException("due_date phải lớn hơn thời điểm hiện tại ít nhất 1 giờ")
    if payload.assignee_id is not None:
        is_assignee_member = db.query(CampaignMember).filter(
            CampaignMember.campaign_id == campaign_id, CampaignMember.user_id == payload.assignee_id
        ).first()
        if not is_assignee_member and campaign.owner_id != payload.assignee_id:
            raise BadRequestException("Người được gán không thuộc chiến dịch này")
    
    new_task = CampaignTask(
        campaign_id=campaign_id, title=payload.title.strip(), description=payload.description,
        due_date=payload.due_date or datetime.now(timezone.utc)+timedelta(days=3),
        priority=payload.priority.upper() if payload.priority else "MEDIUM",
        status=payload.status.upper() if payload.status else "TODO",
        assignee_id=payload.assignee_id or user_id
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


def get_campaign_tasks(campaign_id: int, db: Session, user_id: int, page: int = 1, size: int = 10,
                       sort_by: str = "created_at", order: str = "desc", status: str | None = None,
                       priority: str | None = None, assignee_id: int | None = None, search: str | None = None):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.is_deleted == False).first()
    if not campaign:
        raise NotFoundException("Không tìm thấy chiến dịch")
    is_member = db.query(CampaignMember).filter(
        CampaignMember.user_id == user_id, CampaignMember.campaign_id == campaign_id
    ).first()
    if not is_member and campaign.owner_id != user_id:
        raise ForbiddenException("Bạn không phải thành viên của chiến dịch này")
    query = db.query(CampaignTask).filter(CampaignTask.campaign_id == campaign_id)
    if status:
        query = query.filter(CampaignTask.status == status.strip().upper())
    if priority:
        query = query.filter(CampaignTask.priority == priority.strip().upper())
    if assignee_id is not None:
        query = query.filter(CampaignTask.assignee_id == assignee_id)
    if search:
        query = query.filter(CampaignTask.title.ilike(f"%{search.strip()}%"))
    query = apply_sorting(query, sort_by=sort_by, order=order)
    return paginate(query, page=page, size=size)


def get_campaign_task_by_id(task_id: int, user_id: int, db: Session) -> CampaignTask:
    task = db.query(CampaignTask).filter(CampaignTask.id == task_id).first()
    if not task:
        raise NotFoundException("Task không tồn tại")
    campaign = db.query(Campaign).filter(Campaign.id == task.campaign_id, Campaign.is_deleted == False).first()
    if not campaign:
        raise NotFoundException("Chiến dịch không tồn tại")
    is_member = db.query(CampaignMember).filter(
        CampaignMember.campaign_id == campaign.id, CampaignMember.user_id == user_id
    ).first()
    if not is_member and campaign.owner_id != user_id:
        raise ForbiddenException("Bạn không phải thành viên của chiến dịch này")
    return task


def update_campaign_task(task_id: int, db: Session, user_id: int, payload: CampaignTaskUpdate) -> CampaignTask:
    task = db.query(CampaignTask).filter(CampaignTask.id == task_id).first()
    if not task:
        raise NotFoundException("Task không tồn tại")
    campaign = db.query(Campaign).filter(Campaign.id == task.campaign_id, Campaign.is_deleted == False).first()
    if not campaign:
        raise NotFoundException("Campaign không tồn tại")
    is_owner = (campaign.owner_id == user_id)
    is_assignee = (task.assignee_id == user_id)
    if not is_owner and not is_assignee:
        raise ForbiddenException("Bạn không có quyền chỉnh sửa task này")
    update_data = payload.model_dump(exclude_unset=True)
    if not is_owner and is_assignee:
        if set(update_data.keys()) - {"status"}:
            raise ForbiddenException("Assignee chỉ có quyền cập nhật trạng thái (status) của task")
    if "title" in update_data:
        if update_data["title"] is None or not str(update_data["title"]).strip():
            raise BadRequestException("Tiêu đề công việc không được để trống")
        update_data["title"] = str(update_data["title"]).strip()
    if "assignee_id" in update_data and update_data["assignee_id"] is not None:
        is_assignee_member = db.query(CampaignMember).filter(
            CampaignMember.campaign_id == campaign.id, CampaignMember.user_id == update_data["assignee_id"]
        ).first()
        if not is_assignee_member and campaign.owner_id != update_data["assignee_id"]:
            raise BadRequestException("Người được gán không thuộc chiến dịch này")
    if "status" in update_data:
        if not update_data["status"] or str(update_data["status"]).upper() not in VALID_TASK_STATUSES:
            raise BadRequestException("Trạng thái không hợp lệ (chỉ chấp nhận TODO, IN_PROGRESS, DONE)")
        update_data["status"] = str(update_data["status"]).upper()
    if "priority" in update_data:
        if not update_data["priority"] or str(update_data["priority"]).upper() not in VALID_TASK_PRIORITIES:
            raise BadRequestException("Độ ưu tiên không hợp lệ (chỉ chấp nhận LOW, MEDIUM, HIGH)")
        update_data["priority"] = str(update_data["priority"]).upper()
    if "due_date" in update_data and update_data["due_date"] is not None:
        if _as_utc(update_data["due_date"]) < datetime.now(timezone.utc) + timedelta(hours=1):
            raise BadRequestException("due_date phải lớn hơn thời điểm hiện tại ít nhất 1 giờ")
    for field, value in update_data.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


def delete_campaign_task(task_id: int, db: Session, user_id: int):
    task = db.query(CampaignTask).filter(CampaignTask.id == task_id).first()
    if not task:
        raise NotFoundException("Task không tồn tại")
    campaign = db.query(Campaign).filter(Campaign.id == task.campaign_id, Campaign.is_deleted == False).first()
    if not campaign:
        raise NotFoundException("Campaign không tồn tại")
    if campaign.owner_id != user_id:
        raise ForbiddenException("Chỉ chủ chiến dịch mới có quyền xóa task")
    db.delete(task)
    db.commit()
    return {"message": "Xóa task thành công"}


# ── TASK COMMENT ─────────────────────────────────────────────────────────────

def create_task_comment(task_id: int, user_id: int, payload: TaskCommentCreate, db: Session) -> TaskComment:
    task = db.query(CampaignTask).filter(CampaignTask.id == task_id).first()
    if not task:
        raise NotFoundException("Task không tồn tại")
    campaign = db.query(Campaign).filter(Campaign.id == task.campaign_id, Campaign.is_deleted == False).first()
    if not campaign:
        raise NotFoundException("Chiến dịch không tồn tại")
    is_member = db.query(CampaignMember).filter(
        CampaignMember.campaign_id == campaign.id, CampaignMember.user_id == user_id
    ).first()
    if not is_member and campaign.owner_id != user_id:
        raise ForbiddenException("Bạn không phải thành viên của chiến dịch này")
    if not payload.content or not payload.content.strip():
        raise BadRequestException("Nội dung bình luận không được để trống")
    new_comment = TaskComment(task_id=task_id, user_id=user_id, content=payload.content.strip())
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return new_comment


def get_task_comments(task_id: int, user_id: int, db: Session, page: int = 1,
                      size: int = 10, sort_by: str = "created_at", order: str = "asc"):
    task = db.query(CampaignTask).filter(CampaignTask.id == task_id).first()
    if not task:
        raise NotFoundException("Task không tồn tại")
    campaign = db.query(Campaign).filter(Campaign.id == task.campaign_id, Campaign.is_deleted == False).first()
    if not campaign:
        raise NotFoundException("Chiến dịch không tồn tại")
    is_member = db.query(CampaignMember).filter(
        CampaignMember.campaign_id == campaign.id, CampaignMember.user_id == user_id
    ).first()
    if not is_member and campaign.owner_id != user_id:
        raise ForbiddenException("Bạn không phải thành viên của chiến dịch này")
    query = db.query(TaskComment).filter(TaskComment.task_id == task_id)
    is_desc = (order or "asc").lower() == "desc"
    query = query.order_by(TaskComment.created_at.desc() if is_desc else TaskComment.created_at.asc())
    return paginate(query, page=page, size=size)
