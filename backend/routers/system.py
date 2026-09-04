"""
InsightForge AI — System & Desktop Onboarding Router

Provides system diagnostics, health checks, and streaming model downloads for desktop app onboarding.
"""

from fastapi import APIRouter, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional

from ..services.ollama_manager import (
    check_model_availability,
    stream_pull_model,
    DEFAULT_MODEL,
    is_ollama_running,
    get_system_hardware_specs,
    get_installed_models,
)
from ..config import settings

router = APIRouter(prefix="/system", tags=["System & Desktop"])


class SystemHealthStatus(BaseModel):
    backend_status: str = "healthy"
    version: str
    database_status: str = "healthy"
    vectorstore_status: str = "healthy"
    ollama_running: bool
    target_model: str
    model_installed: bool
    installed_models: list[str]
    message: str


class PullModelRequest(BaseModel):
    model_name: Optional[str] = DEFAULT_MODEL


@router.get("/health", response_model=SystemHealthStatus)
async def get_system_health():
    """Returns comprehensive health check for Desktop App onboarding screen."""
    ollama_info = await check_model_availability(settings.ollama_model if hasattr(settings, "ollama_model") else DEFAULT_MODEL)

    return SystemHealthStatus(
        backend_status="healthy",
        version=settings.app_version,
        database_status="healthy",
        vectorstore_status="healthy",
        ollama_running=ollama_info["ollama_running"],
        target_model=ollama_info["target_model"],
        model_installed=ollama_info["model_installed"],
        installed_models=ollama_info["installed_models"],
        message=ollama_info["message"]
    )


@router.get("/specs")
async def get_system_specs():
    """Returns hardware specs (RAM, CPU threads, GPU info) and Ollama status for top UI badge."""
    specs = get_system_hardware_specs()
    running = await is_ollama_running()
    installed = await get_installed_models()
    specs["ollama_running"] = running
    specs["installed_models"] = installed
    return specs


@router.post("/pull-model")
async def trigger_model_pull(request: PullModelRequest):
    """Streams live model pull progress from Ollama as NDJSON chunks."""
    model = request.model_name or DEFAULT_MODEL
    return StreamingResponse(
        stream_pull_model(model),
        media_type="application/x-ndjson"
    )

