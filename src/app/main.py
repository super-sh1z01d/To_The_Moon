import logging
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Load environment variables from .env file
from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

from src.core.config import get_config
from src.core.json_logging import configure_logging
from src.scheduler.service import init_scheduler
from .spa import mount_spa
from .routes.meta import router as meta_router
from .routes.settings import router as settings_router
from .routes.tokens import router as tokens_router
from .routes.ui import router as ui_router
from .routes.admin import router as admin_router
from .routes.logs import router as logs_router
from .routes.notarb import router as notarb_router
from .routes.health import router as health_router
from .logs_buffer import attach_buffer_handler


def create_app() -> FastAPI:
    cfg = get_config()
    configure_logging(level=cfg.log_level, service=cfg.app_name, version=cfg.app_version, env=cfg.app_env)
    # Attach in-memory buffer for logs API
    attach_buffer_handler()
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
        
        # Initialize monitoring systems
        try:
            # Initialize structured logging
            from src.monitoring.metrics import get_structured_logger
            structured_logger = get_structured_logger("startup")
            structured_logger.set_context(
                service=cfg.app_name,
                version=cfg.app_version,
                environment=cfg.app_env
            )
            
            # Initialize health monitor
            from src.monitoring.health_monitor import get_health_monitor
            health_monitor = get_health_monitor()
            structured_logger.info("Health monitor initialized")
            
            # Initialize performance tracker
            from src.monitoring.metrics import get_performance_tracker
            performance_tracker = get_performance_tracker()
            structured_logger.info("Performance tracker initialized")
            
            # Initialize performance degradation detector
            from src.monitoring.metrics import get_performance_degradation_detector
            degradation_detector = get_performance_degradation_detector()
            structured_logger.info("Performance degradation detector initialized")
            
            # Initialize intelligent alerting engine
            from src.monitoring.alert_manager import get_intelligent_alerting_engine
            intelligent_alerting = get_intelligent_alerting_engine()
            structured_logger.info("Intelligent alerting engine initialized")
            
            # Initialize priority processor
            from src.scheduler.monitoring import get_priority_processor
            priority_processor = get_priority_processor()
            structured_logger.info("Priority processor initialized")
            
            # Initialize configuration hot reloader
            from src.scheduler.monitoring import get_config_hot_reloader
            config_reloader = get_config_hot_reloader()
            config_reloader.start_monitoring()
            structured_logger.info("Configuration hot reloader started")
            
            # Initialize self-healing scheduler wrapper (production only)
            if cfg.app_env == "prod":
                try:
                    from src.scheduler.monitoring import get_self_healing_wrapper
                    self_healing_wrapper = get_self_healing_wrapper()
                    app.state.self_healing_wrapper = self_healing_wrapper
                    structured_logger.info("Self-healing scheduler wrapper initialized")
                except Exception as e:
                    structured_logger.error("Failed to initialize self-healing wrapper", error=e)
            
            # Store monitoring components in app state
            app.state.health_monitor = health_monitor
            app.state.performance_tracker = performance_tracker
            app.state.degradation_detector = degradation_detector
            app.state.intelligent_alerting = intelligent_alerting
            app.state.priority_processor = priority_processor
            app.state.config_reloader = config_reloader
            app.state.structured_logger = structured_logger
            
            structured_logger.info("All monitoring systems initialized successfully")
            
        except Exception as e:
            logging.getLogger("lifecycle").error(
                "Failed to initialize monitoring systems",
                extra={"extra": {"error": str(e)}}
            )
            # Don't fail startup if monitoring fails
        
        # Запуск планировщика
        init_scheduler(app)

    @app.on_event("shutdown")
    async def _shutdown() -> None:  # noqa: D401
        logging.getLogger("lifecycle").info(
            "shutdown", extra={"extra": {"service": cfg.app_name, "env": cfg.app_env, "version": cfg.app_version}}
        )
        
        # Shutdown monitoring systems
        try:
            structured_logger = getattr(app.state, "structured_logger", None)
            if structured_logger:
                structured_logger.info("Shutting down monitoring systems")
            
            # Stop configuration hot reloader
            config_reloader = getattr(app.state, "config_reloader", None)
            if config_reloader:
                config_reloader.stop_monitoring()
                if structured_logger:
                    structured_logger.info("Configuration hot reloader stopped")
            
            # Cleanup alert manager
            from src.monitoring.alert_manager import get_alert_manager
            alert_manager = get_alert_manager()
            alert_manager.cleanup_old_history(days_to_keep=1)  # Cleanup on shutdown
            
            if structured_logger:
                structured_logger.info("Monitoring systems shutdown completed")
                
        except Exception as e:
            logging.getLogger("lifecycle").error(
                "Error during monitoring systems shutdown",
                extra={"extra": {"error": str(e)}}
            )
        
        # Shutdown scheduler
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
    app.include_router(logs_router)
    app.include_router(notarb_router)
    app.include_router(health_router)

    # Static SPA (if built)
    mount_spa(app)

    return app


app = create_app()
