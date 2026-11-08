"""文件路由：上传、下载、删除。"""

import logging
import os
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse, Response
from sqlalchemy.orm import Session

from config import Config
from database import get_db
from models.file import File as FileModel
from models.project import Project
from models.user import User
from utils.auth import login_required, require_project_access, user_can_access_project
from utils.template import render, flash

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)

_EXT_RE = re.compile(r"^\.[A-Za-z0-9]{1,10}$")


def _safe_ebc_step(value: Optional[str]) -> str:
    """Only canonical EBC step names may enter a filesystem path."""
    return value if value in Config.EBC_STEPS else ""


def _safe_extension(filename: str) -> str:
    ext = os.path.splitext(os.path.basename(filename or ""))[1].lower()
    return ext if _EXT_RE.match(ext) else ""


def _too_large(request: Request) -> bool:
    try:
        return int(request.headers.get("content-length", "0")) > Config.MAX_CONTENT_LENGTH
    except (TypeError, ValueError):
        return False


async def _store_upload(uploaded_file, project_id: int, ebc_step: str) -> tuple[str, str, int]:
    original_filename = os.path.basename(uploaded_file.filename or "")
    ext = _safe_extension(original_filename)
    unique_name = f"{uuid.uuid4().hex}{ext}"
    upload_dir = os.path.join(Config.UPLOAD_FOLDER, str(int(project_id)), _safe_ebc_step(ebc_step))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, unique_name)

    written = 0
    try:
        with open(file_path, "wb") as handle:
            while True:
                chunk = await uploaded_file.read(65536)
                if not chunk:
                    break
                written += len(chunk)
                if written > Config.MAX_CONTENT_LENGTH:
                    raise ValueError("upload_too_large")
                handle.write(chunk)
    except Exception:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise

    return unique_name, original_filename, written


@router.get("/projects/{project_id}/files")
async def file_list(
    project_id: int,
    request: Request,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    require_project_access(db, current_user, project_id)
    ebc_step = request.query_params.get("ebc_step", "")
    query = db.query(FileModel).filter(FileModel.project_id == project_id)
    if ebc_step:
        query = query.filter(FileModel.ebc_step == ebc_step)
    files = query.order_by(FileModel.created_at.desc()).all()
    return JSONResponse([f.to_dict() for f in files])


@router.post("/projects/{project_id}/files/upload")
async def upload_file(
    project_id: int,
    request: Request,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    try:
        project = db.query(Project).get(project_id)
        if not project:
            return JSONResponse({"error": "项目不存在"}, status_code=404)
        require_project_access(db, current_user, project_id)

        if _too_large(request):
            return JSONResponse({"error": "文件超过大小限制"}, status_code=413)

        form = await request.form()
        uploaded_file = form.get("file")
        if not uploaded_file or uploaded_file.filename == "":
            return JSONResponse({"error": "未选择文件"}, status_code=400)

        ebc_step = _safe_ebc_step(form.get("ebc_step", ""))
        unique_name, original_filename, file_size = await _store_upload(
            uploaded_file, project_id, ebc_step
        )

        fm = FileModel(
            project_id=project_id,
            ebc_step=ebc_step,
            filename=unique_name,
            original_filename=original_filename,
            file_size=file_size,
            file_type=uploaded_file.content_type or "",
            uploaded_by=current_user.id,
        )
        db.add(fm)
        db.commit()

        if request.headers.get("HX-Request"):
            files = db.query(FileModel).filter(FileModel.project_id == project_id).order_by(FileModel.created_at.desc()).all()
            from starlette.templating import Jinja2Templates
            t = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))
            return t.TemplateResponse("includes/file_items.html", {"request": request, "files": files})

        return JSONResponse(fm.to_dict())

    except HTTPException:
        raise
    except ValueError as exc:
        db.rollback()
        if str(exc) == "upload_too_large":
            return JSONResponse({"error": "文件超过大小限制"}, status_code=413)
        logger.exception("Upload rejected")
        return JSONResponse({"error": "上传失败，请检查文件"}, status_code=400)
    except Exception:
        db.rollback()
        logger.exception("Upload failed for project %s", project_id)
        if request.headers.get("HX-Request"):
            return Response(
                content="上传失败，请稍后重试",
                status_code=200,
                headers={"HX-Reswap": "innerHTML"},
                media_type="text/html",
            )
        return JSONResponse({"error": "上传失败，请稍后重试"}, status_code=500)


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: int,
    request: Request,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    fm = db.query(FileModel).get(file_id)
    if not fm:
        return RedirectResponse(url="/files", status_code=303)
    require_project_access(db, current_user, fm.project_id)

    file_path = os.path.join(
        Config.UPLOAD_FOLDER,
        str(fm.project_id),
        _safe_ebc_step(fm.ebc_step),
        os.path.basename(fm.filename),
    )
    if not os.path.exists(file_path):
        return RedirectResponse(url="/files", status_code=303)

    return FileResponse(
        path=file_path,
        filename=fm.original_filename,
        media_type="application/octet-stream",
    )


@router.post("/projects/{project_id}/files/{file_id}/delete")
async def delete_file(
    project_id: int,
    file_id: int,
    request: Request,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    if not current_user.is_admin():
        return JSONResponse({"error": "权限不足"}, status_code=403)
    require_project_access(db, current_user, project_id)

    fm = db.query(FileModel).get(file_id)
    if not fm or fm.project_id != project_id:
        return JSONResponse({"error": "文件不存在"}, status_code=404)

    file_path = os.path.join(
        Config.UPLOAD_FOLDER,
        str(fm.project_id),
        _safe_ebc_step(fm.ebc_step),
        os.path.basename(fm.filename),
    )
    if os.path.exists(file_path):
        os.remove(file_path)

    db.delete(fm)
    db.commit()

    if request.headers.get("HX-Request"):
        files = db.query(FileModel).filter(FileModel.project_id == project_id).order_by(FileModel.created_at.desc()).all()
        from starlette.templating import Jinja2Templates
        t = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))
        return t.TemplateResponse("includes/file_items.html", {"request": request, "files": files})

    return JSONResponse({"success": True})


@router.get("/projects/{project_id}/files/view")
async def file_view_page(
    project_id: int,
    request: Request,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    project = db.query(Project).get(project_id)
    if not project:
        return RedirectResponse(url="/gantt")
    require_project_access(db, current_user, project_id)
    return render(request, "project_files.html", project=project)


@router.get("/projects/{project_id}/files/list")
async def file_list_html(
    project_id: int,
    request: Request,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    project = db.query(Project).get(project_id)
    if not project:
        return Response(content="项目不存在", status_code=404, media_type="text/plain")
    require_project_access(db, current_user, project_id)

    ebc_step = request.query_params.get("ebc_step", "")
    query = db.query(FileModel).filter(FileModel.project_id == project_id)
    if ebc_step:
        query = query.filter(FileModel.ebc_step == ebc_step)
    files = query.order_by(FileModel.created_at.desc()).all()
    from starlette.templating import Jinja2Templates
    t = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))
    return t.TemplateResponse("includes/file_items.html", {"request": request, "files": files})


@router.post("/projects/{project_id}/files/upload-simple")
async def upload_file_simple(
    project_id: int,
    request: Request,
    current_user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    try:
        project = db.query(Project).get(project_id)
        if not project:
            return RedirectResponse(url="/files", status_code=303)
        require_project_access(db, current_user, project_id)

        if _too_large(request):
            resp = RedirectResponse(url="/files", status_code=303)
            flash(resp, "文件超过大小限制", "error")
            return resp

        form = await request.form()
        uploaded_file = form.get("file")
        if not uploaded_file or uploaded_file.filename == "":
            return RedirectResponse(url="/files", status_code=303)

        ebc_step = _safe_ebc_step(form.get("ebc_step", ""))
        unique_name, original_filename, file_size = await _store_upload(
            uploaded_file, project_id, ebc_step
        )

        fm = FileModel(
            project_id=project_id,
            ebc_step=ebc_step,
            filename=unique_name,
            original_filename=original_filename,
            file_size=file_size,
            file_type=uploaded_file.content_type or "",
            uploaded_by=current_user.id,
        )
        db.add(fm)
        db.commit()

        resp = RedirectResponse(url="/files", status_code=303)
        flash(resp, "文件上传成功", "success")
        return resp

    except HTTPException:
        raise
    except ValueError as exc:
        db.rollback()
        resp = RedirectResponse(url="/files", status_code=303)
        if str(exc) == "upload_too_large":
            flash(resp, "文件超过大小限制", "error")
        else:
            flash(resp, "上传失败，请检查文件", "error")
        return resp
    except Exception:
        db.rollback()
        logger.exception("Upload failed for project %s", project_id)
        resp = RedirectResponse(url="/files", status_code=303)
        flash(resp, "上传失败，请稍后重试", "error")
        return resp
