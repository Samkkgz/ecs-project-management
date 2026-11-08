"""项目路由：总览、甘特图、文件、成员。"""

import logging
from datetime import date as dt_date, timedelta, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from config import Config
from database import get_db
from models.project import Project, ProjectMember
from models.task import Task
from models.user import User
from models.file import File as FileModel
from utils.auth import (
    login_required,
    admin_required,
    require_project_access,
    user_can_access_project,
    safe_next_url,
)
from utils.template import render, flash

router = APIRouter()
logger = logging.getLogger(__name__)


def _accessible_projects(db: Session, user: User):
    if user.is_super_admin():
        return db.query(Project).order_by(Project.sort_order).all()
    return (
        db.query(Project)
        .join(ProjectMember)
        .filter(ProjectMember.user_id == user.id)
        .order_by(Project.sort_order)
        .all()
    )


def _cookie_project_id(request: Request):
    pid = request.cookies.get("project_id", "")
    try:
        return int(pid)
    except (TypeError, ValueError):
        return None


@router.get("/dashboard")
async def dashboard(
    request: Request,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    projects = _accessible_projects(db, current_user)
    project_stats = {}
    for p in projects:
        project_stats[p.id] = p.get_stats(db)

    return render(request, "dashboard.html", projects=projects, project_stats=project_stats)


@router.get("/gantt")
async def gantt(
    request: Request,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    project = None
    project_id = _cookie_project_id(request)
    if project_id:
        candidate = db.query(Project).get(project_id)
        if candidate and user_can_access_project(db, current_user, candidate.id):
            project = candidate

    if project is None:
        available = _accessible_projects(db, current_user)
        project = available[0] if available else None
        if project is None:
            return render(request, "project_gantt.html", project=None, tasks=[], stats=None,
                         months=[], days=[], timeline_width=0, task_data=[], today_str="",
                         today_left=0, filters={})
        resp = RedirectResponse(url="/gantt", status_code=303)
        resp.set_cookie("project_id", str(project.id), max_age=86400 * 30, path="/")
        return resp

    filters = {
        "ebc": request.query_params.get("filter_ebc", ""),
        "phase": request.query_params.get("filter_phase", ""),
        "status": request.query_params.get("filter_status", ""),
        "type": request.query_params.get("filter_type", ""),
    }
    q = Task.query_ordered(db, project.id)
    if filters["ebc"]:
        q = q.filter(Task.ebc_step == filters["ebc"])
    if filters["phase"]:
        q = q.filter(Task.phase == filters["phase"])
    if filters["status"]:
        q = q.filter(Task.status == filters["status"])
    if filters["type"] == "milestone":
        q = q.filter(Task.is_milestone == True)
    elif filters["type"] == "task":
        q = q.filter(Task.is_milestone == False)
    tasks = q.all()
    stats = project.get_stats(db)

    # Calculate date range
    min_date = max_date = None
    for t in tasks:
        if t.start_date:
            if not min_date or t.start_date < min_date:
                min_date = t.start_date
        if t.end_date:
            if not max_date or t.end_date > max_date:
                max_date = t.end_date

    DAY = 30
    if not min_date or not max_date:
        months, days, timeline_width = [], [], 0
        task_data = []
    else:
        min_date = min_date - timedelta(days=5)
        max_date = max_date + timedelta(days=10)
        total_days = (max_date - min_date).days
        timeline_width = total_days * DAY + 40

        months = []
        cursor = min_date
        while cursor < max_date:
            m_end = cursor.replace(day=28) + timedelta(days=4)
            m_end = m_end.replace(day=1)
            span = min((m_end - cursor).days, (max_date - cursor).days)
            months.append({"label": f"{cursor.year}年{cursor.month}月", "width": span * DAY})
            cursor = m_end
            if cursor >= max_date:
                break

        days = [(min_date + timedelta(days=i)).day for i in range(total_days)]

        task_data = []
        for t in tasks:
            bar_left = 0
            bar_width = 0
            if t.start_date and t.end_date:
                bar_left = (t.start_date - min_date).days * DAY
                bar_width = (t.end_date - t.start_date).days * DAY + DAY
            task_data.append({
                "id": t.id,
                "ebc_step": t.ebc_step,
                "phase": t.phase,
                "content": t.content or "",
                "deliverable": t.deliverable or "",
                "company": t.company or "",
                "person_responsible": t.person_responsible or "",
                "status": t.status,
                "start_date": t.start_date,
                "end_date": t.end_date,
                "is_milestone": t.is_milestone,
                "is_draft": t.is_draft,
                "bar_left": bar_left,
                "bar_width": bar_width,
            })

    today_str = dt_date.today().isoformat()
    today_left = (dt_date.today() - min_date).days * DAY if min_date else 0

    return render(request, "project_gantt.html", project=project, tasks=tasks, stats=stats,
                 months=months, days=days, timeline_width=timeline_width,
                 task_data=task_data, today_str=today_str, today_left=today_left,
                 ebc_steps=Config.EBC_STEPS, phases=Config.PHASES,
                 task_statuses=Config.TASK_STATUSES, filters=filters)


@router.get("/files")
async def files_page(
    request: Request,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    project_id = _cookie_project_id(request)
    if not project_id:
        return RedirectResponse(url="/gantt", status_code=303)

    project = db.query(Project).get(project_id)
    if not project:
        return RedirectResponse(url="/gantt", status_code=303)
    require_project_access(db, current_user, project_id)

    ebc_step = request.query_params.get("ebc_step", "")
    query = db.query(FileModel).filter(FileModel.project_id == project.id)
    if ebc_step:
        query = query.filter(FileModel.ebc_step == ebc_step)
    file_list = query.order_by(FileModel.created_at.desc()).all()

    from starlette.templating import Jinja2Templates
    import os as _os
    _local_tmpl = Jinja2Templates(directory=_os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "templates"))
    from utils.template import get_common_context
    _ctx = get_common_context(request)
    _ctx["project"] = project
    _ctx["files"] = file_list
    _tmpl = _local_tmpl.get_template("project_files.html")
    return HTMLResponse(_tmpl.render(_ctx))


@router.get("/users")
async def project_users(
    request: Request,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    project_id = _cookie_project_id(request)
    if not project_id:
        return RedirectResponse(url="/gantt", status_code=303)

    project = db.query(Project).get(project_id)
    if not project:
        return RedirectResponse(url="/gantt", status_code=303)
    require_project_access(db, current_user, project_id)

    members = db.query(ProjectMember).filter(ProjectMember.project_id == project.id).all()
    member_users = [m.user for m in members]
    all_users = db.query(User).order_by(User.username).all() if current_user.is_admin() else []
    return render(request, "project_users.html", project=project, members=member_users, all_users=all_users)


@router.post("/users/add")
async def add_user(
    request: Request,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    project_id = _cookie_project_id(request)
    form = await request.form()
    user_id = form.get("user_id")
    if project_id and user_id:
        require_project_access(db, current_user, project_id)
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            user_id = None
        if user_id and db.query(User).get(user_id):
            existing = db.query(ProjectMember).filter_by(project_id=project_id, user_id=user_id).first()
            if not existing:
                db.add(ProjectMember(project_id=project_id, user_id=user_id))
                db.commit()
    resp = RedirectResponse(url="/users", status_code=303)
    flash(resp, "用户已添加到项目", "success")
    return resp


@router.post("/users/remove/{user_id}")
async def remove_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    project_id = _cookie_project_id(request)
    if project_id:
        require_project_access(db, current_user, project_id)
        pm = db.query(ProjectMember).filter_by(project_id=project_id, user_id=user_id).first()
        if pm:
            db.delete(pm)
            db.commit()
    resp = RedirectResponse(url="/users", status_code=303)
    flash(resp, "用户已从项目移除", "success")
    return resp


@router.get("/set-project/{project_id}")
async def set_project(
    project_id: int,
    request: Request,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    project = db.query(Project).get(project_id)
    if not project:
        return RedirectResponse(url="/gantt", status_code=303)
    require_project_access(db, current_user, project_id)

    resp = RedirectResponse(url=safe_next_url(request.query_params.get("next"), "/gantt"), status_code=303)
    resp.set_cookie("project_id", str(project.id), max_age=86400 * 30, path="/")
    return resp


@router.post("/projects/create")
async def create_project(
    request: Request,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    form = await request.form()
    name = form.get("name", "").strip()
    if not name:
        resp = RedirectResponse(url="/gantt", status_code=303)
        flash(resp, "项目名称不能为空", "error")
        return resp
    max_order = db.query(Project.sort_order).order_by(Project.sort_order.desc()).first()
    next_order = (max_order[0] or 0) + 1 if max_order else 1
    project = Project(name=name, sort_order=next_order)
    db.add(project)
    db.flush()
    if not current_user.is_super_admin():
        db.add(ProjectMember(project_id=project.id, user_id=current_user.id))
    db.commit()
    resp = RedirectResponse(url="/gantt", status_code=303)
    resp.set_cookie("project_id", str(project.id), max_age=86400 * 30, path="/")
    flash(resp, f"项目「{name}」创建成功", "success")
    return resp


@router.get("/admin/seed-ogd")
async def seed_ogd_import(
    request: Request,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    from seed_ogd import TASKS

    project = db.query(Project).filter(Project.name == "Garden OGD Project").first()
    if not project:
        project = Project(name="Garden OGD Project", status="进行中", sort_order=1)
        db.add(project)
        db.flush()
        if not current_user.is_super_admin():
            db.add(ProjectMember(project_id=project.id, user_id=current_user.id))
    else:
        require_project_access(db, current_user, project.id)
        db.query(Task).filter(Task.project_id == project.id).delete()
        db.flush()

    for i, (ebc, phase, content, deliverable, company, person, status, start_str, end_str, is_milestone, _) in enumerate(TASKS):
        sd = datetime.strptime(start_str, "%Y-%m-%d").date() if start_str else None
        ed = datetime.strptime(end_str, "%Y-%m-%d").date() if end_str else None
        task = Task(
            project_id=project.id, ebc_step=ebc, phase=phase, content=content,
            deliverable=deliverable, company=company, person_responsible=person,
            status=status, start_date=sd, end_date=ed, is_milestone=is_milestone,
            is_draft=False, sort_order=i,
        )
        db.add(task)
    db.commit()
    resp = RedirectResponse(url="/gantt", status_code=303)
    flash(resp, f"Garden OGD Project 数据导入完成！共 {len(TASKS)} 条任务", "success")
    return resp


@router.get("/api/projects/{project_id}/stats")
async def api_stats(
    project_id: int,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    project = db.query(Project).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    require_project_access(db, current_user, project_id)
    return project.get_stats(db)
