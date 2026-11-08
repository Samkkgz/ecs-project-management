import os
import secrets
from pathlib import Path
from typing import List, Dict


_WEAK_SECRETS = {
    "",
    "change-this-in-container-manager-env",
    "change-this-to-a-random-secret-key-in-production",
    "changeme",
    "secret",
}


def _default_data_dir() -> Path:
    if os.path.isdir("/data"):
        return Path("/data")
    return Path(__file__).resolve().parent.parent / "data"


def _load_or_create_secret(env_name: str, file_name: str) -> str:
    """Prefer a strong env value; otherwise persist a generated secret on disk.

    Known placeholder values are deliberately ignored so a compose template
    cannot accidentally become the production signing key.
    """
    value = os.environ.get(env_name, "").strip()
    if value and value not in _WEAK_SECRETS and len(value) >= 32:
        return value

    secret_path = Path(os.environ.get(f"{env_name}_FILE") or (_default_data_dir() / file_name))
    try:
        stored = secret_path.read_text(encoding="utf-8").strip()
        if stored and stored not in _WEAK_SECRETS and len(stored) >= 32:
            return stored
    except OSError:
        pass

    generated = secrets.token_urlsafe(48)
    try:
        secret_path.parent.mkdir(parents=True, exist_ok=True)
        secret_path.write_text(generated, encoding="utf-8")
        os.chmod(secret_path, 0o600)
    except OSError:
        pass
    return generated


class Config:
    SECRET_KEY: str = _load_or_create_secret("SECRET_KEY", ".app_secret")
    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL",
        "sqlite:////volume1/docker/ecs-pm/data/ecs_pm.db",
    )
    UPLOAD_FOLDER: str = os.environ.get("UPLOAD_FOLDER", "/data/files")
    MAX_CONTENT_LENGTH: int = int(os.environ.get("MAX_CONTENT_LENGTH", 50 * 1024 * 1024))

    # JWT
    JWT_SECRET: str = _load_or_create_secret("JWT_SECRET", ".jwt_secret")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # Session / login protection
    COOKIE_SECURE: bool = os.environ.get("COOKIE_SECURE", "true").strip().lower() not in ("0", "false", "no")
    LOGIN_MAX_ATTEMPTS: int = int(os.environ.get("LOGIN_MAX_ATTEMPTS", 5))
    LOGIN_WINDOW_SECONDS: int = int(os.environ.get("LOGIN_WINDOW_SECONDS", 900))

    EBC_STEPS: List[str] = [
        "Visioning",
        "Fesibility",
        "Development",
        "Commissioning",
        "Implementation & Nurture",
        "Continue Improvement",
    ]

    PHASES: List[str] = ["准备阶段", "项目实施", "实施阶段", "回顾阶段"]

    TASK_STATUSES: List[str] = ["待开始", "进行中", "完成"]

    PROJECT_STATUSES: List[str] = ["进行中", "已完成", "待开始"]

    USER_ROLES: List[str] = ["user", "admin", "super_admin"]

    USER_STATUSES: List[str] = ["pending", "active"]

    EBC_STEP_ORDER: Dict[str, int] = {step: i for i, step in enumerate(EBC_STEPS)}

    VERSION: str = "v2.0.5"


# Export module-level constants for easy import
DATABASE_URL = Config.DATABASE_URL
