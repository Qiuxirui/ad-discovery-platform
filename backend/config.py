"""应用配置。

所有路径一律由 ``Path(__file__)`` 推导，禁止出现盘符或绝对路径；
所有可调参数经 ``ADX_`` 前缀环境变量注入，未设置时使用代码内默认值。
"""

from __future__ import annotations

import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
STATIC_DIR = BACKEND_DIR / "static"
COVERS_DIR = STATIC_DIR / "covers"
UPLOADS_DIR = STATIC_DIR / "uploads"
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
SECRET_FILE = BACKEND_DIR / ".secret"


def _load_or_create_secret() -> str:
    """读取本地密钥文件；不存在则生成并落盘（首次启动免配置）。"""
    env_secret = _read_env_secret()
    if env_secret:
        return env_secret
    try:
        if SECRET_FILE.exists():
            value = SECRET_FILE.read_text(encoding="utf-8").strip()
            if len(value) >= 32:
                return value
        value = secrets.token_hex(32)
        SECRET_FILE.write_text(value, encoding="utf-8")
        return value
    except OSError:
        # 只读文件系统（如某些测试环境）下退化为进程内随机密钥，功能不受影响
        return secrets.token_hex(32)


def _read_env_secret() -> str:
    """从环境变量读取密钥，避免 import 阶段依赖 pydantic 实例化顺序。"""
    import os

    return os.environ.get("ADX_SECRET", "").strip()


class Settings(BaseSettings):
    """运行时配置（ADX_ 前缀）。"""

    model_config = SettingsConfigDict(env_prefix="ADX_", case_sensitive=False, extra="ignore")

    # 数据库：留空则落到 backend/data/adx.db
    db_path: str = ""
    # JWT/Cookie 签名密钥，留空则自动读取或生成 backend/.secret
    secret: str = ""
    # 生产环境（https）应置 1，本地 http 必须为 0，否则浏览器不回传 Cookie
    cookie_secure: bool = False
    # 初始管理员
    admin_username: str = "admin"
    admin_display_name: str = "运营管理员"
    admin_password: str = "adx-admin-2026"
    # 登录态有效期（秒），默认 3 天
    token_ttl_seconds: int = 259200
    # 定时任务开关（测试可关）
    scheduler_enabled: bool = True
    # 定时任务轮询间隔（秒）
    scheduler_interval_seconds: int = 60
    # CORS 允许来源（仅开发态使用，逗号分隔）
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"

    @property
    def resolved_db_path(self) -> Path:
        """数据库文件绝对路径（由项目目录推导，或取 ADX_DB_PATH）。"""
        if self.db_path:
            candidate = Path(self.db_path)
            if not candidate.is_absolute():
                candidate = BACKEND_DIR / candidate
            return candidate
        return DATA_DIR / "adx.db"

    @property
    def resolved_secret(self) -> str:
        """签名密钥：环境变量 > 配置文件 > 自动生成的 .secret 文件。"""
        if self.secret and len(self.secret) >= 16:
            return self.secret
        return _load_or_create_secret()

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


_settings: Settings | None = None


def get_settings() -> Settings:
    """返回全局唯一 Settings 实例（懒加载）。"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings_cache() -> None:
    """清空缓存（测试切换 ADX_DB_PATH 时使用）。"""
    global _settings
    _settings = None
