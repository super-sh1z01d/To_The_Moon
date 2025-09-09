import logging
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.config import get_config
from src.core.json_logging import configure_logging
from src.scheduler.service import init_scheduler
from .spa import mount_spa
from .routes.meta import router as meta_router
from .routes.settings import router as settings_router
from .routes.tokens import router as tokens_router
from .routes.ui import router as ui_router
from .routes.admin import router as admin_router


def create_app() -> FastAPI:
    cfg = get_config()
    configure_logging(level=cfg.log_level, service=cfg.app_name, version=cfg.app_version, env=cfg.app_env)
    app = FastAPI(title=cfg.app_name, version=cfg.app_version)

    # Middlewares
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # dev: открыт, для prod сузим
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def access_logger(request: Request, call_next):  # noqa: D401
        start = time.perf_counter()
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception as e:  # noqa: BLE001
            status = 500
            logging.getLogger("request").exception(
                "unhandled_exception",
                extra={"extra": {"path": request.url.path, "method": request.method}},
            )
            raise e
        finally:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logging.getLogger("access").info(
                "request_completed",
                extra={
                    "extra": {
                        "path": request.url.path,
                        "method": request.method,
                        "status": status,
                        "latency_ms": elapsed_ms,
                    }
                },
            )
        return response

    @app.on_event("startup")
    async def _startup() -> None:  # noqa: D401
        logging.getLogger("lifecycle").info(
            "startup",
            extra={"extra": {"service": cfg.app_name, "env": cfg.app_env, "version": cfg.app_version}},
        )
        # Запуск планировщика
        init_scheduler(app)

    @app.on_event("shutdown")
    async def _shutdown() -> None:  # noqa: D401
        logging.getLogger("lifecycle").info(
            "shutdown", extra={"extra": {"service": cfg.app_name, "env": cfg.app_env, "version": cfg.app_version}}
        )
        sched = getattr(app.state, "scheduler", None)
        if sched:
            try:
                sched.shutdown(wait=False)
            except Exception:  # noqa: BLE001
                pass

    # Exception handlers (унифицированный формат ошибок)
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):  # noqa: D401
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "path": str(request.url.path),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):  # noqa: D401
        logging.getLogger("errors").exception(
            "unhandled_error", extra={"extra": {"path": request.url.path, "type": type(exc).__name__}}
        )
        return JSONResponse(
            status_code=500,
            content={"error": {"code": 500, "message": "Internal Server Error", "path": str(request.url.path)}},
        )

    # Routers
    app.include_router(meta_router)
    app.include_router(settings_router)
    app.include_router(tokens_router)
    app.include_router(ui_router)
    app.include_router(admin_router)

    # Static SPA (if built)
    mount_spa(app)

    return app


app = create_app()
