import math
from sqlalchemy.orm import Session, Query
from sqlalchemy import or_, asc, desc

from core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from core.security import hash_pass, verify_pass
from datetime import datetime
from schemas.user import UserCreate, UserLogin
from schemas.campaign import CampaignCreate, CampaignUpdate, CampaignPatch
from schemas.campaign_task import CampaignTaskCreate, CampaignTaskUpdate
from schemas.task_comment import TaskCommentCreate
from models.user import User
from models.campaign import Campaign, CampaignMember
from models.campaign_task import CampaignTask
from models.task_comment import TaskComment


def paginate(query: Query, page: int = 1, size: int = 10) -> dict:
    page = page or 1
    size = size or 10
    if page < 1:
        page = 1
    if size < 1:
        size = 10

    total = query.count()
    total_pages = math.ceil(total / size) if size > 0 else 0
    items = query.offset((page - 1) * size).limit(size).all()

    return {
        "total": total,
        "page": page,
        "size": size,
        "total_pages": total_pages,
        "items": items,
    }


def apply_sorting(
    query: Query,
    sort_by: str = "created_at",
    order: str = "desc",
) -> Query:
    col = CampaignTask.due_date if sort_by == "due_date" else CampaignTask.created_at
    is_desc = (order or "desc").lower() == "desc"
    return query.order_by(col.desc() if is_desc else col.asc())



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


def get_users(
    db: Session,
    page: int = 1,
    size: int = 10,
    sort_by: str = "id",
    order: str = "asc",
    search: str | None = None,
    is_active: bool | None = None
):
    query = db.query(User)

    if search:
        search = search.strip()
        query = query.filter(
            (User.full_name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%"))
        )

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    _sort_map = {"id": User.id, "full_name": User.full_name, "email": User.email, "role": User.role}
    col = _sort_map.get(sort_by, User.id)
    is_desc = (order or "asc").lower() == "desc"
    query = query.order_by(col.desc() if is_desc else col.asc())

    return paginate(query, page=page, size=size)


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


def list_campaigns(
    db: Session,
    user_id: int,
    page: int = 1,
    size: int = 10,
    search: str | None = None
):
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

    query = query.order_by(Campaign.created_at.desc())

    return paginate(query, page=page, size=size)


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

    if not campaign and campaign:
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


VALID_TASK_STATUSES = {"TODO", "IN_PROGRESS", "DONE"}
VALID_TASK_PRIORITIES = {"LOW", "MEDIUM", "HIGH"}


def add_campaign_task(campaign_id: int, db: Session, user_id: int, payload: CampaignTaskCreate) -> CampaignTask:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.is_deleted == False).first()
    if not campaign:
        raise NotFoundException('Không tìm thấy chiến dịch')
    is_member = db.query(CampaignMember).filter(CampaignMember.user_id == user_id, CampaignMember.campaign_id == campaign_id).first()
    if not is_member and campaign.owner_id != user_id:
        raise ForbiddenException('Bạn không phải thành viên của chiến dịch này')

    if payload.status and payload.status.upper() not in VALID_TASK_STATUSES:
        raise BadRequestException("Trạng thái không hợp lệ (chỉ chấp nhận TODO, IN_PROGRESS, DONE)")

    if payload.priority and payload.priority.upper() not in VALID_TASK_PRIORITIES:
        raise BadRequestException("Độ ưu tiên không hợp lệ (chỉ chấp nhận LOW, MEDIUM, HIGH)")

    if payload.assignee_id is not None:
        is_assignee_member = db.query(CampaignMember).filter(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == payload.assignee_id
        ).first()
        if not is_assignee_member and campaign.owner_id != payload.assignee_id:
            raise BadRequestException('Người được gán không thuộc chiến dịch này')

    new_task = CampaignTask(  
        campaign_id=campaign_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        priority=payload.priority.upper() if payload.priority else "MEDIUM",
        status=payload.status.upper() if payload.status else "TODO",
        assignee_id=payload.assignee_id
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task



def get_campaign_tasks(
    campaign_id: int,
    db: Session,
    user_id: int,
    page: int = 1,
    size: int = 10,
    sort_by: str = "created_at",
    order: str = "desc",
    status: str | None = None,
    priority: str | None = None,
    assignee_id: int | None = None,
    search: str | None = None,
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.is_deleted == False).first()
    if not campaign:
        raise NotFoundException('Không tìm thấy chiến dịch')
    is_member = db.query(CampaignMember).filter(CampaignMember.user_id == user_id, CampaignMember.campaign_id == campaign_id).first()
    if not is_member and campaign.owner_id != user_id:
        raise ForbiddenException('Bạn không phải thành viên của chiến dịch này')

    query = db.query(CampaignTask).filter(CampaignTask.campaign_id == campaign_id)

    if status:
        query = query.filter(CampaignTask.status == status)
    if priority:
        query = query.filter(CampaignTask.priority == priority)
    if assignee_id is not None:
        query = query.filter(CampaignTask.assignee_id == assignee_id)
    if search:
        search = search.strip()
        query = query.filter(CampaignTask.title.ilike(f"%{search}%"))

    query = apply_sorting(query, sort_by=sort_by, order=order)

    return paginate(query, page=page, size=size)


def get_campaign_task_by_id(task_id: int, user_id: int, db: Session) -> CampaignTask:
    task = db.query(CampaignTask).filter(CampaignTask.id == task_id).first()
    if not task:
        raise NotFoundException("Task không tồn tại")

    campaign = db.query(Campaign).filter(
        Campaign.id == task.campaign_id,
        Campaign.is_deleted == False
    ).first()
    if not campaign:
        raise NotFoundException("Chiến dịch không tồn tại")

    is_member = db.query(CampaignMember).filter(
        CampaignMember.campaign_id == campaign.id,
        CampaignMember.user_id == user_id
    ).first()
    if not is_member and campaign.owner_id != user_id:
        raise ForbiddenException("Bạn không phải thành viên của chiến dịch này")

    return task


def update_campaign_task(
    task_id: int,
    db: Session,
    user_id: int,
    payload: CampaignTaskUpdate
) -> CampaignTask:
    task = db.query(CampaignTask).filter(CampaignTask.id == task_id).first()
    if not task:
        raise NotFoundException("Task không tồn tại")

    campaign = db.query(Campaign).filter(
        Campaign.id == task.campaign_id,
        Campaign.is_deleted == False
    ).first()
    if not campaign:
        raise NotFoundException("Campaign không tồn tại")

    is_owner = (campaign.owner_id == user_id)
    is_assignee = (task.assignee_id == user_id)

    # 1. Nếu không phải Owner và không phải Assignee của task -> Chặn 403
    if not is_owner and not is_assignee:
        raise ForbiddenException("Bạn không có quyền chỉnh sửa task này")

    update_data = payload.model_dump(exclude_unset=True)

    # 2. Nếu là Assignee (không phải Owner): Chỉ được phép đổi status của task
    if not is_owner and is_assignee:
        other_fields = set(update_data.keys()) - {"status"}
        if other_fields:
            raise ForbiddenException("Assignee chỉ có quyền cập nhật trạng thái (status) của task")

    # 3. Nếu là Owner gán/đổi assignee_id mới: Người được gán phải thuộc chiến dịch
    if "assignee_id" in update_data and update_data["assignee_id"] is not None:
        is_assignee_member = db.query(CampaignMember).filter(
            CampaignMember.campaign_id == campaign.id,
            CampaignMember.user_id == update_data["assignee_id"]
        ).first()
        if not is_assignee_member and campaign.owner_id != update_data["assignee_id"]:
            raise BadRequestException("Người được gán không thuộc chiến dịch này")

    if "status" in update_data and update_data["status"] is not None:
        if update_data["status"].upper() not in VALID_TASK_STATUSES:
            raise BadRequestException("Trạng thái không hợp lệ (chỉ chấp nhận TODO, IN_PROGRESS, DONE)")
        update_data["status"] = update_data["status"].upper()

    if "priority" in update_data and update_data["priority"] is not None:
        if update_data["priority"].upper() not in VALID_TASK_PRIORITIES:
            raise BadRequestException("Độ ưu tiên không hợp lệ (chỉ chấp nhận LOW, MEDIUM, HIGH)")
        update_data["priority"] = update_data["priority"].upper()

    for field, value in update_data.items():
        setattr(task, field, value)


    db.commit()
    db.refresh(task)
    return task


def delete_campaign_task(
    task_id: int,
    db: Session,
    user_id: int
):
    task = db.query(CampaignTask).filter(CampaignTask.id == task_id).first()
    if not task:
        raise NotFoundException("Task không tồn tại")

    campaign = db.query(Campaign).filter(
        Campaign.id == task.campaign_id,
        Campaign.is_deleted == False
    ).first()
    if not campaign:
        raise NotFoundException("Campaign không tồn tại")

    # Chỉ duy nhất Owner mới có quyền xóa task
    if campaign.owner_id != user_id:
        raise ForbiddenException("Chỉ chủ chiến dịch mới có quyền xóa task")

    db.delete(task)
    db.commit()
    return {"message": "Xóa task thành công"}


def create_task_comment(
    task_id: int,
    user_id: int,
    payload: TaskCommentCreate,
    db: Session
) -> TaskComment:
    task = db.query(CampaignTask).filter(CampaignTask.id == task_id).first()
    if not task:
        raise NotFoundException("Task không tồn tại")

    campaign = db.query(Campaign).filter(
        Campaign.id == task.campaign_id,
        Campaign.is_deleted == False
    ).first()
    if not campaign:
        raise NotFoundException("Chiến dịch không tồn tại")

    is_member = db.query(CampaignMember).filter(
        CampaignMember.campaign_id == campaign.id,
        CampaignMember.user_id == user_id
    ).first()
    if not is_member and campaign.owner_id != user_id:
        raise ForbiddenException("Bạn không phải thành viên của chiến dịch này")

    new_comment = TaskComment(
        task_id=task_id,
        user_id=user_id,
        content=payload.content.strip()
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return new_comment


def get_task_comments(
    task_id: int,
    user_id: int,
    db: Session,
    page: int = 1,
    size: int = 10,
    sort_by: str = "created_at",
    order: str = "asc"
):
    task = db.query(CampaignTask).filter(CampaignTask.id == task_id).first()
    if not task:
        raise NotFoundException("Task không tồn tại")

    campaign = db.query(Campaign).filter(
        Campaign.id == task.campaign_id,
        Campaign.is_deleted == False
    ).first()
    if not campaign:
        raise NotFoundException("Chiến dịch không tồn tại")

    is_member = db.query(CampaignMember).filter(
        CampaignMember.campaign_id == campaign.id,
        CampaignMember.user_id == user_id
    ).first()
    if not is_member and campaign.owner_id != user_id:
        raise ForbiddenException("Bạn không phải thành viên của chiến dịch này")

    query = db.query(TaskComment).filter(TaskComment.task_id == task_id)
    is_desc = (order or "asc").lower() == "desc"
    query = query.order_by(TaskComment.created_at.desc() if is_desc else TaskComment.created_at.asc())

    return paginate(query, page=page, size=size)


