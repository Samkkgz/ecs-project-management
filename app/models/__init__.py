import os
import secrets
from pathlib import Path

from database import Base
from config import Config
from models.user import User
from models.project import Project, ProjectMember
from models.task import Task
from models.file import File


def _initial_admin_credentials():
    """Never ship a fixed bootstrap password.

    Use INITIAL_ADMIN_PASSWORD when provided; otherwise generate a random one
    and persist it to a 0600 file so the operator can retrieve it once.
    """
    password = os.environ.get("INITIAL_ADMIN_PASSWORD", "").strip()
    password_file = None
    if len(password) < 8:
        password = secrets.token_urlsafe(18)
        base = Path("/data") if os.path.isdir("/data") else Path(__file__).resolve().parent.parent.parent / "data"
        password_file = base / "initial_admin_password.txt"
        try:
            password_file.parent.mkdir(parents=True, exist_ok=True)
            password_file.write_text(password, encoding="utf-8")
            os.chmod(password_file, 0o600)
        except OSError:
            password_file = None
    email = os.environ.get("INITIAL_ADMIN_EMAIL", "sam.lu@ecsomni.com").strip()
    return email, password, password_file


def seed_defaults():
    """Create default admin user if no users exist. Called from init_db()."""
    from database import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
        if result == 0:
            email, password, password_file = _initial_admin_credentials()
            admin = User(
                email=email,
                username="系统管理员",
                company="ECS",
                role="super_admin",
                status="active",
            )
            admin.set_password(password)
            db.add(admin)
            db.commit()
            if password_file:
                print(f"[seed] generated initial admin password at {password_file}")
            return True
        return False
    finally:
        db.close()
