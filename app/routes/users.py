"""用户管理路由：用户 CRUD、系统管理面板。"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from config import Config
from database import get_db
from models.user import User
from models.project import Project, ProjectMember
from models.task import Task
from utils.auth import login_required, admin_required, super_admin_required
from utils.template import render, flash

router = APIRouter(prefix="/admin")

MIN_PASSWORD_LENGTH = 8


def _valid_role(value: str) -> bool:
    return value in Config.USER_ROLES


def _error(message: str, url: str = "/admin/users"):
    resp = RedirectResponse(url=url, status_code=303)
    flash(resp, message, "error")
    return resp


@router.get("/users")
async def user_list(
    request: Request,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return render(request, "admin_users.html", users=users)


@router.post("/users/create")
async def create_user(
    request: Request,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    form = await request.form()
    email = form.get("email", "").strip()
    username = form.get("username", "").strip()
    company = form.get("company", "").strip()
    password = form.get("password", "").strip()
    role = form.get("role", "user")

    if not email or not username or not password:
        return _error("邮箱、用户名和密码不能为空")
    if len(password) < MIN_PASSWORD_LENGTH:
        return _error(f"密码至少需要 {MIN_PASSWORD_LENGTH} 位")
    if not _valid_role(role):
        return _error("无效的用户角色")
    if not current_user.is_super_admin() and role != "user":
        return _error("只有超级管理员可以创建管理员账号")

    if db.query(User).filter(User.email == email).first():
        return _error("该邮箱已被注册")

    user = User(email=email, username=username, company=company, role=role, status="active")
    user.set_password(password)
    db.add(user)
    db.commit()
    resp = RedirectResponse(url="/admin/users", status_code=303)
    flash(resp, f"用户 {username} 创建成功", "success")
    return resp


@router.post("/users/{user_id}/edit")
async def edit_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    user = db.query(User).get(user_id)
    if not user:
        return RedirectResponse(url="/admin/users", status_code=303)

    if not current_user.is_super_admin() and (user.is_admin() or user.id == current_user.id):
        return _error("只有超级管理员可以修改管理员账号")

    form = await request.form()
    new_role = form.get("role", user.role)
    if not _valid_role(new_role):
        return _error("无效的用户角色")
    if not current_user.is_super_admin():
        new_role = user.role

    user.username = form.get("username", user.username)
    user.company = form.get("company", user.company)
    user.role = new_role
    user.status = form.get("status", user.status)

    new_password = form.get("password", "").strip()
    if new_password:
        if len(new_password) < MIN_PASSWORD_LENGTH:
            return _error(f"密码至少需要 {MIN_PASSWORD_LENGTH} 位")
        user.set_password(new_password)

    db.commit()
    resp = RedirectResponse(url="/admin/users", status_code=303)
    flash(resp, f"用户 {user.username} 已更新", "success")
    return resp


@router.post("/users/{user_id}/delete")
async def delete_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(super_admin_required),
    db: Session = Depends(get_db),
):
    user = db.query(User).get(user_id)
    if not user:
        return RedirectResponse(url="/admin/users", status_code=303)

    if user.id == current_user.id:
        return _error("不能删除自己")

    if user.is_super_admin():
        remaining = db.query(User).filter(User.role == "super_admin", User.id != user.id).count()
        if remaining == 0:
            return _error("系统必须至少保留一个超级管理员")

    db.delete(user)
    db.commit()
    resp = RedirectResponse(url="/admin/users", status_code=303)
    flash(resp, f"用户 {user.username} 已删除", "success")
    return resp


@router.get("/api/users")
async def api_user_list(
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return JSONResponse([u.to_dict() for u in users])


@router.get("")
@router.get("/")
async def admin_panel(
    request: Request,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    tab = request.query_params.get("tab", "projects")
    selected_project_id = request.query_params.get("project")
    if selected_project_id:
        try:
            selected_project_id = int(selected_project_id)
        except (ValueError, TypeError):
            selected_project_id = None
    projects = db.query(Project).order_by(Project.sort_order).all()
    for p in projects:
        p.task_count = db.query(Task).filter(Task.project_id == p.id, Task.is_draft.is_(False)).count()
    users = db.query(User).order_by(User.created_at.desc()).all()
    all_users = db.query(User).order_by(User.username).all()

    project_members = {}
    selected_project = None
    for p in projects:
        members = db.query(ProjectMember).filter(ProjectMember.project_id == p.id).all()
        project_members[p.id] = [m.user for m in members]
        if selected_project_id and p.id == selected_project_id:
            selected_project = p

    return render(request, "admin_dashboard.html",
                  projects=projects, users=users,
                  tab=tab,
                  selected_project=selected_project,
                  selected_project_id=selected_project_id,
                  all_users=all_users, project_members=project_members)


@router.post("/projects/{project_id}/members/add")
async def add_project_member(
    project_id: int,
    request: Request,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    form = await request.form()
    user_id = form.get("user_id")
    if user_id:
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            user_id = None
        if user_id and db.query(User).get(user_id):
            existing = db.query(ProjectMember).filter_by(project_id=project_id, user_id=user_id).first()
            if not existing:
                db.add(ProjectMember(project_id=project_id, user_id=user_id))
                db.commit()
    resp = RedirectResponse(url="/admin", status_code=303)
    flash(resp, "成员已添加", "success")
    return resp


@router.post("/projects/{project_id}/members/remove/{user_id}")
async def remove_project_member(
    project_id: int,
    user_id: int,
    request: Request,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    pm = db.query(ProjectMember).filter_by(project_id=project_id, user_id=user_id).first()
    if pm:
        db.delete(pm)
        db.commit()
    resp = RedirectResponse(url="/admin", status_code=303)
    flash(resp, "成员已移除", "success")
    return resp


@router.get("/projects")
async def project_list(
    request: Request,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    projects = db.query(Project).order_by(Project.sort_order).all()
    for p in projects:
        p.task_count = db.query(Task).filter(Task.project_id == p.id, Task.is_draft.is_(False)).count()
    return render(request, "admin_projects.html", projects=projects)


@router.post("/projects/create")
async def create_project(
    request: Request,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    form = await request.form()
    name = form.get("name", "").strip()
    if not name:
        return _error("项目名称不能为空", "/admin")
    status = form.get("status", "进行中")
    try:
        sort_order = int(form.get("sort_order", 0))
    except (TypeError, ValueError):
        sort_order = 0
    project = Project(name=name, status=status, sort_order=sort_order)
    db.add(project)
    db.flush()
    if not current_user.is_super_admin():
        db.add(ProjectMember(project_id=project.id, user_id=current_user.id))
    db.commit()
    resp = RedirectResponse(url="/admin", status_code=303)
    flash(resp, f"项目「{name}」创建成功", "success")
    return resp


@router.post("/projects/{project_id}/edit")
async def edit_project(
    project_id: int,
    request: Request,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    project = db.query(Project).get(project_id)
    if not project:
        return RedirectResponse(url="/admin", status_code=303)

    form = await request.form()
    project.name = form.get("name", project.name)
    project.status = form.get("status", project.status)
    try:
        project.sort_order = int(form.get("sort_order", project.sort_order))
    except (TypeError, ValueError):
        pass
    db.commit()
    resp = RedirectResponse(url="/admin", status_code=303)
    flash(resp, f"项目「{project.name}」已更新", "success")
    return resp


@router.post("/projects/{project_id}/delete")
async def delete_project(
    project_id: int,
    request: Request,
    current_user: User = Depends(super_admin_required),
    db: Session = Depends(get_db),
):
    project = db.query(Project).get(project_id)
    if not project:
        return RedirectResponse(url="/admin", status_code=303)
    name = project.name
    db.delete(project)
    db.commit()
    resp = RedirectResponse(url="/admin", status_code=303)
    flash(resp, f"项目「{name}」已删除", "success")
    return resp
