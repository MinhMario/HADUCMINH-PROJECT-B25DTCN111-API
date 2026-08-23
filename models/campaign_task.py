from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class CampaignTask(Base):
    __tablename__ = "campaign_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), nullable=False, default="TODO")  # TODO / IN_PROGRESS / DONE
    priority = Column(String(20), nullable=False, default="MEDIUM")  # LOW / MEDIUM / HIGH
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    campaign = relationship("Campaign", back_populates="tasks")
    assignee = relationship("User", back_populates="assigned_tasks")
