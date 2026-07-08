import logging
import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.api.routes.announcements import ws_router
from app.api.routes.messages import ws_router as messages_ws_router
from app.core.config import PROJECT_ROOT, get_settings
from app.core.exceptions import add_exception_handlers
from app.core.logging import configure_logging
from app.schemas.response import ok
from app.services.startup import auto_backup_worker, run_startup_checks


settings = get_settings()
configure_logging(settings)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.logger = logger

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.server.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    add_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)
    app.include_router(ws_router)
    app.include_router(messages_ws_router)

    frontend_dist = PROJECT_ROOT / "frontend" / "dist"
    if frontend_dist.exists():
        # 生产模式：直接托管前端构建产物，并支持 SPA 历史路由刷新回退。
        # 任意 GET 路径若对应真实文件则直接返回；否则（前端路由，如 /student）
        # 回退到 index.html，避免在子路由刷新时返回 404 {"detail":"Not Found"}。
        base = frontend_dist.resolve()

        @app.get("/")
        async def serve_root():
            return FileResponse(frontend_dist / "index.html")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            if not full_path.startswith("api/"):
                candidate = (base / full_path).resolve()
                # 防路径穿越：仅当解析后仍在 frontend_dist 内且为真实文件时才返回
                if candidate.is_relative_to(base) and candidate.is_file():
                    return FileResponse(candidate)
                # 前端路由（刷新时浏览器直接请求该路径）：回退到 index.html
                return FileResponse(frontend_dist / "index.html")
            # /api 下未匹配的路径保持原 404 行为
            raise HTTPException(status_code=404, detail="Not Found")
    else:
        static_dir = Path(__file__).parent / "static"
        static_dir.mkdir(exist_ok=True)
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

        @app.get("/")
        def root():
            return ok({"message": "后端服务已启动，前端尚未构建"})

    @app.on_event("startup")
    async def startup() -> None:
        app.state.startup_checks = run_startup_checks(settings)
        app.state.auto_backup_task = asyncio.create_task(auto_backup_worker())
        logger.info("Application startup checks completed")

    @app.on_event("shutdown")
    async def shutdown() -> None:
        task = getattr(app.state, "auto_backup_task", None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    return app


app = create_app()
