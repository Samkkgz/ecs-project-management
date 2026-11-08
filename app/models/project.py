"""项目与项目成员模型。"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="进行中")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tasks = relationship("Task", backref="project", lazy="dynamic", cascade="all, delete-orphan")
    members = relationship("ProjectMember", backref="project", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "sort_order": self.sort_order,
        }

    def get_stats(self, db_session=None):
        from models.task import Task
        if db_session is None:
            from database import SessionLocal
            db_session = SessionLocal()
            should_close = True
        else:
            should_close = False

        try:
            total = db_session.query(Task).filter(
                Task.project_id == self.id,
                Task.is_draft.is_(False),
            ).count()
            completed = db_session.query(Task).filter(
                Task.project_id == self.id,
                Task.status == "完成",
                Task.is_draft.is_(False),
            ).count()
            in_progress = db_session.query(Task).filter(
                Task.project_id == self.id,
                Task.status == "进行中",
                Task.is_draft.is_(False),
            ).count()
            pending = db_session.query(Task).filter(
                Task.project_id == self.id,
                Task.status == "待开始",
                Task.is_draft.is_(False),
            ).count()
            milestones = db_session.query(Task).filter(
                Task.project_id == self.id,
                Task.is_milestone.is_(True),
                Task.is_draft.is_(False),
            ).count()
            rate = f"{int(completed / total * 100)}%" if total > 0 else "0%"
            return {
                "total": total, "completed": completed,
                "in_progress": in_progress, "pending": pending,
                "milestones": milestones, "rate": rate,
            }
        finally:
            if should_close:
                db_session.close()


class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="project_memberships", lazy=True)

    __table_args__ = (UniqueConstraint("project_id", "user_id"),)
