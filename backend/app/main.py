import logging
import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
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
