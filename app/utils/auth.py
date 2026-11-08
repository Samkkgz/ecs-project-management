"""JWT 认证工具：token 生成、校验、用户依赖注入（cookie 版）。"""

from __future__ import annotations
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from config import Config
from database import get_db
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from models.user import User



def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return bcrypt.hash(password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + timedelta(hours=Config.JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional["User"]:
    from models.user import User
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_access_token(token)
    if payload is None:
        return None
    username: str = payload.get("sub")
    if username is None:
        return None
    user = db.query(User).filter(User.email == username).first()
    if user is None or user.status != "active":
        return None
    return user


def login_required(current_user: Optional[User] = Depends(get_current_user)) -> User:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    return current_user


def admin_required(current_user: User = Depends(login_required)) -> User:
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user


def super_admin_required(current_user: User = Depends(login_required)) -> User:
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级管理员权限",
        )
    return current_user


def user_can_access_project(db: Session, user: "User", project_id: int) -> bool:
    """A user may access a project only as super admin or explicit member."""
    from models.project import ProjectMember

    if user is None or not user.is_active_user():
        return False
    if user.is_super_admin():
        return True
    return (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id)
        .first()
        is not None
    )


def require_project_access(db: Session, user: "User", project_id: int) -> None:
    if not user_can_access_project(db, user, project_id):
        raise HTTPException(status_code=403, detail="无权访问该项目")


def safe_next_url(value: Optional[str], default: str = "/dashboard") -> str:
    """Only allow same-site absolute paths, blocking //evil.com and backslashes."""
    if not value:
        return default
    value = value.strip()
    if not value.startswith("/") or value.startswith("//") or "\\" in value:
        return default
    return value
