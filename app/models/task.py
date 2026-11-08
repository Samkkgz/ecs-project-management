"""任务模型。"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, Date, DateTime, ForeignKey, case
from database import Base
from config import Config


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    ebc_step = Column(String(100), nullable=False)
    phase = Column(String(50), nullable=False, default="准备阶段")
    content = Column(Text, default="")
    deliverable = Column(Text, default="")
    company = Column(String(255), default="")
    person_responsible = Column(String(255), default="")
    status = Column(String(20), nullable=False, default="待开始")
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_milestone = Column(Boolean, default=False)
    is_draft = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "ebc_step": self.ebc_step,
            "phase": self.phase,
            "content": self.content or "",
            "deliverable": self.deliverable or "",
            "company": self.company or "",
            "person_responsible": self.person_responsible or "",
            "status": self.status,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_milestone": self.is_milestone,
            "is_draft": self.is_draft,
            "sort_order": self.sort_order,
        }

    @classmethod
    def query_ordered(cls, db_session, project_id):
        step_order = case(
            {step: i for i, step in enumerate(Config.EBC_STEPS)},
            value=cls.ebc_step,
            else_=len(Config.EBC_STEPS),
        )
        return db_session.query(cls).filter(cls.project_id == project_id).order_by(
            cls.is_draft.desc(),
            step_order,
            cls.start_date.asc().nullslast(),
            cls.id.asc(),
        )
