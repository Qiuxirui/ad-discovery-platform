"""数据库引擎、会话与路径常量。

- SQLite 单文件，连接建立时挂 ``WAL`` / ``foreign_keys`` / ``busy_timeout``；
- 全项目路径一律由 ``Path(__file__)`` 推导。
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import (
    BACKEND_DIR,
    COVERS_DIR,
    DATA_DIR,
    FRONTEND_DIST,
    ROOT_DIR,
    STATIC_DIR,
    UPLOADS_DIR,
    get_settings,
)

__all__ = [
    "BACKEND_DIR",
    "COVERS_DIR",
    "DATA_DIR",
    "DB_PATH",
    "FRONTEND_DIST",
    "ROOT_DIR",
    "STATIC_DIR",
    "UPLOADS_DIR",
    "Base",
    "SessionLocal",
    "engine",
    "get_db",
    "init_db",
]


DB_PATH: Path = get_settings().resolved_db_path
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
for _directory in (DATA_DIR, STATIC_DIR, COVERS_DIR, UPLOADS_DIR):
    _directory.mkdir(parents=True, exist_ok=True)


class Base(DeclarativeBase):
    """ORM 声明基类。"""


engine = create_engine(
    f"sqlite:///{DB_PATH}",
    future=True,
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 15},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # noqa: ANN001, ARG001
    """每个连接都开启 WAL、外键约束与忙等待超时。"""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI 依赖：请求级数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """按 ORM 元数据建表（幂等）。"""
    from . import models  # noqa: F401  确保所有模型已注册到 metadata

    Base.metadata.create_all(bind=engine)
