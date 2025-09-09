from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.core.config import get_config


def mount_spa(app: FastAPI) -> None:
    cfg = get_config()
    dist = cfg.frontend_dist_path
    if dist and os.path.isdir(dist):
        app.mount("/app", StaticFiles(directory=dist, html=True), name="spa")
