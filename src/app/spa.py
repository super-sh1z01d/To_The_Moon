from __future__ import annotations

import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.core.config import get_config


def mount_spa(app: FastAPI) -> None:
    cfg = get_config()
    dist = cfg.frontend_dist_path
    if dist and os.path.isdir(dist):
        # Mount static files first
        if os.path.isdir(f"{dist}/assets"):
            app.mount("/app/assets", StaticFiles(directory=f"{dist}/assets"), name="spa-assets")
        
        # Add catch-all route for SPA
        @app.get("/app/{path:path}")
        async def spa_handler(request: Request, path: str):
            # For SPA routes, always return index.html
            return FileResponse(f"{dist}/index.html")
        
        # Mount root /app route
        @app.get("/app")
        async def spa_root(request: Request):
            return FileResponse(f"{dist}/index.html")
