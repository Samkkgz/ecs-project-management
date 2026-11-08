import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
"""模板渲染辅助工具：render/flash/get_common_context，从 run.py 中移出以解决循环引用。"""

import os
from typing import Optional

from starlette.templating import Jinja2Templates
from fastapi import Request, Response

from config import Config
from database import SessionLocal
from urllib.parse import quote, unquote
from models.user import User
from models.project import Project, ProjectMember

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))


def get_common_context(request: Request) -> dict:
    current_user: Optional[User] = getattr(request.state, "current_user", None)
    db = SessionLocal()
    try:
        if current_user and current_user.is_super_admin():
            projects = db.query(Project).order_by(Project.sort_order).all()
        elif current_user and current_user.is_authenticated:
            projects = (
                db.query(Project)
                .join(ProjectMember)
                .filter(ProjectMember.user_id == current_user.id)
                .order_by(Project.sort_order)
                .all()
            )
        else:
            projects = []
    finally:
        db.close()

    pid = request.cookies.get("project_id")
    current_project = None
    if pid:
        db2 = SessionLocal()
        try:
            current_project = db2.query(Project).get(int(pid))
        except (ValueError, TypeError):
            current_project = None
        finally:
            db2.close()
    if current_project and all(p.id != current_project.id for p in projects):
        current_project = None
    if not current_project and projects:
        current_project = projects[0]

    flash_message = unquote(request.cookies.get("flash_message") or "")
    flash_category = request.cookies.get("flash_category", "success")

    return {
        "request": request,
        "current_user": current_user,
        "version": Config.VERSION,
        "ebc_steps": Config.EBC_STEPS,
        "phases": Config.PHASES,
        "task_statuses": Config.TASK_STATUSES,
        "project_statuses": Config.PROJECT_STATUSES,
        "user_roles": Config.USER_ROLES,
        "user_statuses": Config.USER_STATUSES,
        "nav_projects": projects,
        "current_project": current_project,
        "flash_message": flash_message,
        "flash_category": flash_category,
    }


def render(request: Request, template_name: str, status_code: int = 200, **context):
    ctx = get_common_context(request)
    ctx.update(context)
    response = templates.TemplateResponse(template_name, ctx, status_code=status_code)
    response.delete_cookie("flash_message", path="/")
    response.delete_cookie("flash_category", path="/")
    return response


def flash(response: Response, message: str, category: str = "success"):
    response.set_cookie(key="flash_message", value=quote(message), max_age=60, path="/")
    response.set_cookie(key="flash_category", value=category, max_age=60, path="/")
