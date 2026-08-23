from database import SessionLocal

from core.security import hash_pass
from models.user import User
from models.campaign import Campaign
from models.campaign_task import CampaignTask


def seed_data():
    db = SessionLocal()
    db.query(CampaignTask).delete()
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

    db.close()

    print("Seed dữ liệu thành công!")


if __name__ == "__main__":
    seed_data()