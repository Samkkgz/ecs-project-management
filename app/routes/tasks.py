"""任务路由：CRUD + 甘特图数据。"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from config import Config
from database import get_db
from models.task import Task
from models.project import Project
from models.user import User
from utils.auth import login_required, require_project_access
from utils.template import render, flash

router = APIRouter(prefix="/api")


def htmx_redirect(url: str):
    """Return a 303 redirect so native form POSTs switch to GET.

    A 307 redirect preserves the POST method; following it to a GET-only page
    such as /gantt produces "405 Method Not Allowed".
    """
    resp = RedirectResponse(url=url, status_code=303)
    resp.headers["HX-Redirect"] = url
    return resp


def is_checked(value) -> bool:
    """Normalize checkbox values.

    A checkbox without a value attribute submits "on"; the gantt forms set
    value="1", so both must be treated as checked.
    """
    return str(value or "").strip().lower() in ("on", "1", "true", "yes")


def _parse_date(value: str, field_name: str):
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"{field_name} 格式无效，应为 YYYY-MM-DD")


def _task_for_user(db: Session, task_id: int, user: User) -> Task:
    task = db.query(Task).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    require_project_access(db, user, task.project_id)
    return task


@router.get("/projects/{project_id}/tasks")
async def task_list(
    project_id: int,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    require_project_access(db, current_user, project_id)
    tasks = Task.query_ordered(db, project_id).all()
    return JSONResponse([t.to_dict() for t in tasks])


@router.post("/projects/{project_id}/tasks/create")
async def create_task(
    project_id: int,
    request: Request,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    project = db.query(Project).get(project_id)
    if not project:
        return RedirectResponse(url="/gantt", status_code=303)
    require_project_access(db, current_user, project_id)

    form = await request.form()
    content = form.get("content", "")
    deliverable = form.get("deliverable", "")
    task = Task(
        project_id=project_id,
        ebc_step=form.get("ebc_step", "Visioning"),
        phase=form.get("phase", "准备阶段"),
        content=content,
        deliverable=deliverable,
        company=form.get("company", ""),
        person_responsible=form.get("person_responsible", ""),
        status=form.get("status", "待开始"),
        is_draft=not (content.strip() or deliverable.strip()),
        sort_order=0,
    )

    start_str = form.get("start_date", "").strip()
    end_str = form.get("end_date", "").strip()
    if start_str:
        task.start_date = _parse_date(start_str, "开始日期")
    if end_str:
        task.end_date = _parse_date(end_str, "结束日期")

    task.is_milestone = is_checked(form.get("is_milestone"))
    db.add(task)
    db.commit()

    resp = htmx_redirect(f"/gantt?project_id={project_id}")
    flash(resp, "任务创建成功", "success")
    return resp


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: int,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    task = _task_for_user(db, task_id, current_user)
    return JSONResponse(task.to_dict())


@router.get("/tasks/{task_id}/edit")
async def edit_task_form(
    task_id: int,
    request: Request,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    task = _task_for_user(db, task_id, current_user)
    project = db.query(Project).get(task.project_id)
    from starlette.templating import Jinja2Templates
    import os
    t = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))
    return t.TemplateResponse("includes/task_form.html", {
        "request": request, "task": task, "project": project,
        "ebc_steps": Config.EBC_STEPS, "phases": Config.PHASES,
        "task_statuses": Config.TASK_STATUSES,
    })


@router.get("/tasks/{task_id}/detail")
async def task_detail(
    task_id: int,
    request: Request,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    task = _task_for_user(db, task_id, current_user)
    project = db.query(Project).get(task.project_id)
    from starlette.templating import Jinja2Templates
    import os
    t = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))
    return t.TemplateResponse("includes/task_detail.html", {
        "request": request, "task": task, "project": project,
    })


@router.post("/tasks/{task_id}/update")
async def update_task(
    task_id: int,
    request: Request,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    task = _task_for_user(db, task_id, current_user)

    form = await request.form()
    task.ebc_step = form.get("ebc_step", task.ebc_step)
    task.phase = form.get("phase", task.phase)
    task.content = form.get("content", task.content)
    task.deliverable = form.get("deliverable", task.deliverable)
    task.company = form.get("company", task.company)
    task.person_responsible = form.get("person_responsible", task.person_responsible)
    task.status = form.get("status", task.status)

    start_str = form.get("start_date", "").strip()
    end_str = form.get("end_date", "").strip()
    if start_str:
        task.start_date = _parse_date(start_str, "开始日期")
    if end_str:
        task.end_date = _parse_date(end_str, "结束日期")

    task.is_milestone = is_checked(form.get("is_milestone"))

    if task.content and task.content.strip():
        task.is_draft = False
    if task.deliverable and task.deliverable.strip():
        task.is_draft = False

    db.commit()
    resp = htmx_redirect(f"/gantt?project_id={task.project_id}")
    flash(resp, "任务已更新", "success")
    return resp


@router.post("/tasks/{task_id}/delete")
async def delete_task(
    task_id: int,
    request: Request,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    task = _task_for_user(db, task_id, current_user)

    if not current_user.is_admin():
        raise HTTPException(status_code=403, detail="权限不足")

    project_id = task.project_id
    db.delete(task)
    db.commit()

    resp = RedirectResponse(url=f"/gantt?project_id={project_id}", status_code=303)
    resp.headers["HX-Redirect"] = f"/gantt?project_id={project_id}"
    flash(resp, "任务已删除", "success")
    return resp


@router.post("/tasks/{task_id}/update_dates")
async def update_task_dates(
    task_id: int,
    request: Request,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    """Handle drag-and-drop date updates."""
    task = _task_for_user(db, task_id, current_user)

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求格式无效")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="请求格式无效")

    start_str = body.get("start_date")
    end_str = body.get("end_date")
    if start_str:
        task.start_date = _parse_date(start_str, "开始日期")
    if end_str:
        task.end_date = _parse_date(end_str, "结束日期")

    if task.content and task.content.strip():
        task.is_draft = False

    db.commit()
    return JSONResponse(task.to_dict())
