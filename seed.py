from app.db.database import SessionLocal
from app.core.security import hash_pass
from app.models.user import User
from app.models.campaign import Campaign, CampaignMember
from app.models.campaign_task import CampaignTask
from app.models.task_comment import TaskComment


def seed_data():
    db = SessionLocal()
    db.query(TaskComment).delete()
    db.query(CampaignTask).delete()
    db.query(CampaignMember).delete()
    db.query(Campaign).delete()
    db.query(User).delete()
    db.commit()

    user1 = User(
        email="admin@gmail.com",
        full_name="Admin",
        password_hash=hash_pass("admin123"),
        role="ADMIN",
        is_active=True,
    )

    user2 = User(
        email="user@gmail.com",
        full_name="User",
        password_hash=hash_pass("user123"),
        role="USER",
        is_active=True,
    )

    db.add_all([user1, user2])
    db.commit()
    db.refresh(user1)
    db.refresh(user2)

    campaign1 = Campaign(
        name="Summer Campaign",
        description="Chiến dịch mùa hè",
        owner_id=user1.id,
    )

    db.add(campaign1)
    db.commit()
    db.refresh(campaign1)

    member1 = CampaignMember(
        campaign_id=campaign1.id,
        user_id=user1.id,
        role="OWNER",
    )
    member2 = CampaignMember(
        campaign_id=campaign1.id,
        user_id=user2.id,
        role="MEMBER",
    )
    db.add_all([member1, member2])
    db.commit()

    task1 = CampaignTask(
        title="Thiết kế banner",
        status="TODO",
        campaign_id=campaign1.id,
        assignee_id=user2.id,
    )

    task2 = CampaignTask(
        title="Viết content",
        status="IN_PROGRESS",
        campaign_id=campaign1.id,
        assignee_id=user1.id,
    )

    db.add_all([task1, task2])
    db.commit()
    db.refresh(task1)
    db.refresh(task2)

    comment1 = TaskComment(
        task_id=task1.id,
        user_id=user2.id,
        content="Đã chuẩn bị mockup kích thước 1200x628px cho Facebook ads.",
    )
    comment2 = TaskComment(
        task_id=task1.id,
        user_id=user1.id,
        content="Ok duyệt, nhớ dùng tone màu thương hiệu nhé!",
    )
    db.add_all([comment1, comment2])
    db.commit()

    db.close()

    print("Seed data successfully!")



if __name__ == "__main__":
    seed_data()