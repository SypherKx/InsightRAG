"""
InsightForge AI — System & Desktop Onboarding Router

Provides system diagnostics, health checks, and streaming model downloads for desktop app onboarding.
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

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


class HardwareModeRequest(BaseModel):
    mode: str = "cpu"


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


@router.get("/hardware-mode")
async def get_hardware_mode():
    """Get active hardware acceleration mode and GPU eligibility details."""
    from ..dependencies import get_rag_service
    rag_svc = get_rag_service()
    if hasattr(rag_svc, "get_hardware_mode"):
        return rag_svc.get_hardware_mode()
    from ..services.ollama_manager import get_system_hardware_specs
    return get_system_hardware_specs()


@router.post("/hardware-mode")
async def switch_hardware_mode(request: HardwareModeRequest):
    """Switch processing between GPU and CPU at runtime with live terminal logs."""
    from ..dependencies import get_rag_service
    from ..services.ollama_manager import set_active_hardware_mode
    rag_svc = get_rag_service()
    set_active_hardware_mode(request.mode)
    if hasattr(rag_svc, "set_hardware_mode"):
        result = rag_svc.set_hardware_mode(request.mode)
        return result
    return {"mode": request.mode, "status": "updated"}


@router.post("/pull-model")
async def trigger_model_pull(request: PullModelRequest):
    """Streams live model pull progress from Ollama as NDJSON chunks."""
    model = request.model_name or DEFAULT_MODEL
    return StreamingResponse(
        stream_pull_model(model),
        media_type="application/x-ndjson"
    )


@router.get("/models")
async def list_available_models():
    """List all installed local Ollama models with their metadata."""
    from ..services.ollama_manager import get_working_ollama_host
    host = await get_working_ollama_host()
    if not host:
        return {"installed_models": [], "models": [], "ollama_running": False}
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(f"{host}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                raw_models = data.get("models", [])
                names = [m.get("name") for m in raw_models if "name" in m]
                return {
                    "installed_models": names,
                    "models": raw_models,
                    "ollama_running": True
                }
    except Exception:
        pass
    return {"installed_models": [], "models": [], "ollama_running": False}


