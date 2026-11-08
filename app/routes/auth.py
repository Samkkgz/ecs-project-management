"""认证路由：登录、登出。"""

from collections import defaultdict, deque
from time import monotonic

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from config import Config
from database import get_db
from models.user import User
from utils.auth import create_access_token, login_required, safe_next_url
from utils.template import render

router = APIRouter()

_login_failures = defaultdict(deque)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_key(request: Request, email: str) -> str:
    return f"{_client_ip(request)}:{email.strip().lower()}"


def _is_rate_limited(key: str) -> bool:
    now = monotonic()
    window = Config.LOGIN_WINDOW_SECONDS
    attempts = _login_failures[key]
    while attempts and now - attempts[0] > window:
        attempts.popleft()
    return len(attempts) >= Config.LOGIN_MAX_ATTEMPTS


def _record_failure(key: str) -> None:
    _login_failures[key].append(monotonic())


@router.get("/login")
async def login_page(request: Request):
    current_user = getattr(request.state, "current_user", None)
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return render(request, "login.html")


@router.post("/login")
async def login_post(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    email = form.get("email", "").strip()
    password = form.get("password", "")
    key = _rate_key(request, email)

    if _is_rate_limited(key):
        return render(
            request,
            "login.html",
            status_code=429,
            error_msg="登录尝试次数过多，请 15 分钟后再试",
            email=email,
        )

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.check_password(password):
        _record_failure(key)
        resp = render(request, "login.html", error_msg="邮箱或密码错误", email=email)
        return resp

    if user.status != "active":
        _record_failure(key)
        resp = render(request, "login.html", error_msg="账号未激活，请联系管理员", email=email)
        return resp

    _login_failures.pop(key, None)
    token = create_access_token(data={"sub": user.email})
    next_page = safe_next_url(request.query_params.get("next"), "/dashboard")
    resp = RedirectResponse(url=next_page, status_code=303)
    resp.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=Config.COOKIE_SECURE,
        max_age=Config.JWT_EXPIRATION_HOURS * 3600,
        samesite="lax",
        path="/",
    )
    return resp


@router.get("/logout")
async def logout(request: Request):
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie("access_token", path="/")
    resp.delete_cookie("project_id", path="/")
    resp.delete_cookie("flash_message", path="/")
    resp.delete_cookie("flash_category", path="/")
    return resp
