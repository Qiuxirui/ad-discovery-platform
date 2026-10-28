"""FastAPI 应用装配（顺序不可变，见架构 §3.2）。

1. 建 app + 异常处理器 → 2. 中间件 → 3. include_router（全部 /api/*）
4. /static 挂载 → 5. /assets 挂载（dist 存在时）→ 6. catch-all SPA fallback（最后注册）
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import FRONTEND_DIST, STATIC_DIR, get_settings
from .database import init_db
from .routers import API_ROUTERS
from .scheduler import scheduler_loop
from .services.ads import ApiError
from .visitor import VisitorMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
audit_log = logging.getLogger("adx.audit")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201, ARG001
    """启动：建表 + 起定时任务；关闭：取消后台协程。"""
    init_db()
    settings = get_settings()
    task: asyncio.Task | None = None
    if settings.scheduler_enabled:
        task = asyncio.create_task(scheduler_loop())
        audit_log.info("scheduler_started interval=%ss", settings.scheduler_interval_seconds)
    audit_log.info("app_startup vendor=adx")
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        audit_log.info("app_shutdown")


app = FastAPI(
    title="广告发现站 API",
    version="1.0.0",
    description="广告自主浏览与智能分类平台 · 后端接口（P0 全量 + 指定 P1）",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


# ------------------------------------------------------------------ 异常处理
@app.exception_handler(ApiError)
async def _handle_api_error(request: Request, exc: ApiError) -> JSONResponse:  # noqa: ARG001
    """业务异常 → ``{"detail", "code", "fields"}``。"""
    payload: dict[str, object] = {"detail": exc.detail, "code": exc.code}
    if exc.fields:
        payload["fields"] = exc.fields
    return JSONResponse(payload, status_code=exc.status_code)


def _translate_validation_message(error: dict) -> str:
    """把 pydantic 英文错误信息转成中文提示。"""
    raw = str(error.get("msg", "格式不正确"))
    if raw.startswith("Value error, "):
        return raw[len("Value error, ") :]
    error_type = str(error.get("type", ""))
    mapping = {
        "missing": "该字段为必填项",
        "string_too_short": "内容不能为空",
        "string_too_long": "内容超出长度上限",
        "too_long": "数量超出上限",
        "int_parsing": "必须是整数",
        "int_type": "必须是整数",
        "bool_parsing": "必须是布尔值",
        "greater_than_equal": "数值过小",
        "less_than_equal": "数值过大",
        "json_invalid": "请求体格式不正确",
    }
    return mapping.get(error_type, raw)


@app.exception_handler(RequestValidationError)
async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:  # noqa: ARG001
    """422：把 pydantic 的 ``loc`` 映射成前端字段名。"""
    fields: list[dict[str, str]] = []
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", ()) if part not in ("body", "query", "path")]
        field = ".".join(location) or "请求体"
        fields.append({"field": field, "message": _translate_validation_message(error)})
    return JSONResponse(
        {
            "detail": f"有 {len(fields)} 项需要修改",
            "code": "VALIDATION_ERROR",
            "fields": fields,
        },
        status_code=422,
    )


@app.exception_handler(StarletteHTTPException)
async def _handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:  # noqa: ARG001
    """统一 HTTP 错误体（``detail`` 为 dict 时透传其 code）。"""
    if isinstance(exc.detail, dict):
        payload = dict(exc.detail)
        payload.setdefault("code", "HTTP_ERROR")
        return JSONResponse(payload, status_code=exc.status_code)
    code_map = {401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
    return JSONResponse(
        {"detail": str(exc.detail), "code": code_map.get(exc.status_code, "HTTP_ERROR")},
        status_code=exc.status_code,
    )


# ------------------------------------------------------------------ 中间件
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(VisitorMiddleware)

# ------------------------------------------------------------------ API 路由
for _router in API_ROUTERS:
    app.include_router(_router)

# ------------------------------------------------------------------ 静态资源
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

if FRONTEND_DIST.exists():
    _assets_dir = FRONTEND_DIST / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")


@app.get("/favicon.ico", include_in_schema=False, response_model=None)
def favicon():
    """前端图标（构建后才存在）。"""
    icon = FRONTEND_DIST / "favicon.ico"
    if icon.exists():
        return FileResponse(icon)
    return JSONResponse({"detail": "图标不存在", "code": "NOT_FOUND"}, status_code=404)


# ------------------------------------------------------------------ SPA fallback（必须最后注册）
@app.get("/{full_path:path}", include_in_schema=False, response_model=None)
def spa_fallback(full_path: str):
    """非 ``/api`` 路径返回前端入口；``/api`` 未知路径必须 404 JSON。"""
    if full_path.split("/", 1)[0] == "api":
        return JSONResponse({"detail": "接口不存在", "code": "NOT_FOUND"}, status_code=404)

    index = FRONTEND_DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse(
        {
            "detail": "前端尚未构建，请先执行 npm --prefix frontend run build，或使用 npm --prefix frontend run dev",
            "code": "FRONTEND_NOT_BUILT",
        },
        status_code=404,
    )
