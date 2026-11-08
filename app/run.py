import sys, os
sys.path.insert(0, os.path.dirname(__file__))
"""ECS 项目管理系统 - FastAPI 应用入口 (v2.0.0)"""

import os
import json
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config import Config
from database import init_db, get_db
from models.user import User
from models.project import Project, ProjectMember
from utils.auth import decode_access_token


# ── Auth middleware ────────────────────────────────────────────

class AuthMiddleware(BaseHTTPMiddleware):
    """Read JWT from cookie and set request.state.current_user."""

    async def dispatch(self, request: Request, call_next):
        token = request.cookies.get("access_token")
        user = None
        if token:
            payload = decode_access_token(token)
            if payload:
                username = payload.get("sub")
                if username:
                    db = next(get_db())
                    try:
                        user = db.query(User).filter(User.email == username).first()
                    finally:
                        db.close()
        request.state.current_user = user
        response = await call_next(request)
        return response


# ── Lifespan ───────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


# ── App ────────────────────────────────────────────────────────

app = FastAPI(
    title="ECS 项目管理系统",
    version=Config.VERSION,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(AuthMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1024)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Baseline browser hardening headers."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; object-src 'none'; "
        "base-uri 'self'; frame-ancestors 'none'",
    )
    response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.middleware("http")
async def cache_headers(request: Request, call_next):
    """静态资源长缓存，个性化 HTML 每次重验证。"""
    response = await call_next(request)
    if request.method == "GET" and request.url.path.startswith("/static/"):
        if response.status_code in (200, 304):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif "text/html" in response.headers.get("content-type", ""):
        response.headers["Cache-Control"] = "private, no-cache, must-revalidate"
    return response

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

from routes.auth import router as auth_router
from routes.projects import router as projects_router
from routes.tasks import router as tasks_router
from routes.files import router as files_router
from routes.users import router as users_router

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(files_router)
app.include_router(users_router)


# ── Template context helper (moved to utils/template.py) ────────

from utils.template import get_common_context, render, flash


# ── Route helpers ──# ── Route helpers ──────────────────────────────────────────────

def get_nav_projects(current_user):
    """Get project list for navigation."""
    from database import SessionLocal
    db = SessionLocal()
    try:
        if current_user and current_user.is_super_admin():
            return db.query(Project).order_by(Project.sort_order).all()
        elif current_user:
            return (
                db.query(Project)
                .join(ProjectMember)
                .filter(ProjectMember.user_id == current_user.id)
                .order_by(Project.sort_order)
                .all()
            )
        return []
    finally:
        db.close()


# ── Root redirect ──────────────────────────────────────────────

@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard")
