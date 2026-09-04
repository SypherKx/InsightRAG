"""
InsightForge AI — FastAPI Backend

Main application entry point.
"""

import os
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add project root and src directory to path for Vercel imports
ROOT_DIR = str(Path(__file__).resolve().parent.parent)
SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from .config import settings
from .storage.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    try:
        settings.ensure_dirs()
        init_db(settings.database_url)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Startup initialization error: {e}", exc_info=True)
    yield
    # Shutdown
    logger.info("Shutting down")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="AI-powered Healthcare & Educational RAG Intelligence Platform",
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from .routers import health, datasets, anomalies, rag, system

app.include_router(health.router, prefix="/api/v1")
app.include_router(datasets.router, prefix="/api/v1")
app.include_router(anomalies.router, prefix="/api/v1")
app.include_router(rag.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")

# Serve static frontend bundle for 100% standalone local execution
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Always prefer dist/client (new Vite TanStack build) over dist root (old build)
DIST_DIR = Path(ROOT_DIR) / "frontend" / "dist"
DIST_CLIENT_DIR = DIST_DIR / "client"

# Fallback: if client dir doesn't exist, use dist root
if not DIST_CLIENT_DIR.exists():
    DIST_CLIENT_DIR = DIST_DIR

if DIST_CLIENT_DIR.exists():
    # Mount assets from client dir
    assets_dir = DIST_CLIENT_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # Mount root static files (favicons, images) from client dir
    app.mount("/static", StaticFiles(directory=str(DIST_CLIENT_DIR)), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve SPA index.html for all non-API frontend routes."""
        if (
            full_path.startswith("api/")
            or full_path.startswith("docs")
            or full_path.startswith("openapi.json")
            or full_path.startswith("static/")
            or full_path.startswith("assets/")
        ):
            return {"error": "Not Found"}

        # Try to serve a matching static file from client dir first
        target_file = DIST_CLIENT_DIR / full_path
        if target_file.exists() and target_file.is_file():
            return FileResponse(str(target_file))

        # Always serve SPA index.html from dist/client
        index_file = DIST_CLIENT_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))

        return {"name": settings.app_name, "version": settings.app_version}

else:
    @app.get("/")
    async def root():
        """Root endpoint fallback."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/api/v1/health",
        }
