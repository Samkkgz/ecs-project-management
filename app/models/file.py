"""文件模型。"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    ebc_step = Column(String(100))
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer)
    file_type = Column(String(100))
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    uploader = relationship("User", backref="uploaded_files", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "ebc_step": self.ebc_step or "",
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "file_type": self.file_type or "",
            "uploaded_by": self.uploaded_by,
            "uploader_name": self.uploader.username if self.uploader else "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def size_display(self):
        if not self.file_size:
            return "-"
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"
