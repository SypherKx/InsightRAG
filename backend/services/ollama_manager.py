"""
InsightForge AI — Ollama & System Manager Service

Manages local Ollama daemon detection, absolute executable resolution, model status checks, and automated background process initialization.
"""

import os
import json
import logging
import subprocess
import asyncio
import shutil
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List, Optional
import httpx

from ..config import settings

logger = logging.getLogger(__name__)

# Default model recommended for InsightForge local RAG
DEFAULT_MODEL = getattr(settings, "ollama_model", "llama3.2:3b")
OLLAMA_HOSTS = ["http://127.0.0.1:11434", "http://localhost:11434"]


def find_ollama_executable() -> str:
    """Find absolute path to ollama executable across standard installation directories."""
    # 1. System PATH
    found = shutil.which("ollama")
    if found:
        return found
        
    # 2. Windows AppData / Program Files paths
    local_appdata = os.getenv("LOCALAPPDATA", "")
    program_files = os.getenv("ProgramFiles", "")
    user_home = str(Path.home())

    candidates = [
        os.path.join(local_appdata, "Programs", "Ollama", "ollama.exe"),
        os.path.join(local_appdata, "Ollama", "ollama.exe"),
        os.path.join(user_home, "AppData", "Local", "Programs", "Ollama", "ollama.exe"),
        os.path.join(program_files, "Ollama", "ollama.exe"),
        "C:\\Program Files\\Ollama\\ollama.exe",
    ]

    for cand in candidates:
        if cand and os.path.exists(cand):
            return cand

    return "ollama"


def try_start_ollama_daemon() -> bool:
    """Attempt to launch `ollama serve` or `ollama.exe` process in background if not already running."""
    ollama_bin = find_ollama_executable()
    try:
        logger.info(f"Attempting background auto-launch of Ollama daemon: {ollama_bin} serve")
        if os.name == 'nt':
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen([ollama_bin, "serve"], creationflags=CREATE_NO_WINDOW)
        else:
            subprocess.Popen([ollama_bin, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        logger.warning(f"Could not auto-launch Ollama daemon: {e}")
        return False


async def get_working_ollama_host(auto_start: bool = True) -> Optional[str]:
    """Check reachable Ollama host, auto-starting `ollama serve` if unavailable."""
    configured = getattr(settings, "ollama_base_url", None) or getattr(settings, "ollama_host", None)
    hosts = [configured] + OLLAMA_HOSTS if configured else OLLAMA_HOSTS
    
    # 1. Initial connectivity check
    for host in hosts:
        if not host:
            continue
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                resp = await client.get(f"{host}/api/tags")
                if resp.status_code == 200:
                    return host
        except Exception:
            continue
    
    # 2. If not running and auto_start enabled, launch `ollama serve` and retry up to 5 times
    if auto_start:
        launched = try_start_ollama_daemon()
        if launched:
            for _ in range(5):
                await asyncio.sleep(1.0)
                for host in hosts:
                    if not host:
                        continue
                    try:
                        async with httpx.AsyncClient(timeout=1.5) as client:
                            resp = await client.get(f"{host}/api/tags")
                            if resp.status_code == 200:
                                logger.info(f"Ollama daemon successfully auto-started on {host}")
                                return host
                    except Exception:
                        continue

    return None


async def is_ollama_running() -> bool:
    """Check if local Ollama service is reachable on port 11434."""
    host = await get_working_ollama_host(auto_start=True)
    return host is not None


async def get_installed_models() -> List[str]:
    """Retrieve list of currently installed Ollama model names."""
    host = await get_working_ollama_host()
    if not host:
        return []
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{host}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", []) if "name" in m]
                return models
    except Exception as e:
        logger.warning(f"Failed to fetch Ollama models: {e}")
    return []


def get_installed_models_sync(host: Optional[str] = None) -> List[str]:
    """Retrieve list of currently installed Ollama model names synchronously."""
    endpoint = host or "http://127.0.0.1:11434"
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{endpoint}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", []) if "name" in m]
                return models
    except Exception:
        pass
    return []


def get_best_available_model_sync(
    requested_model: Optional[str] = None,
    installed: Optional[List[str]] = None,
    host: Optional[str] = None
) -> Optional[str]:
    """
    Synchronously resolves the optimal Ollama model to use.
    If requested_model is installed (exact or prefix), returns it.
    Otherwise returns the best installed chat/text model, or None if no models installed.
    """
    if installed is None:
        installed = get_installed_models_sync(host)
    if not installed:
        return None

    if requested_model:
        # Avoid cloud model strings
        req_clean = requested_model.lower().strip()
        if not req_clean.startswith(("groq", "gemini", "openai", "claude")):
            req_base = req_clean.split(":")[0]
            for m in installed:
                m_lower = m.lower()
                m_base = m_lower.split(":")[0]
                if req_clean == m_lower or req_base == m_base or req_base in m_lower or m_base in req_base:
                    return m

    # Preference ranking for local text/chat models
    for candidate_kw in ["qwen2.5-coder", "qwen2.5", "qwen", "llama3.2", "llama3.1", "llama3", "llama", "mistral", "phi3", "phi", "gemma"]:
        for m in installed:
            if candidate_kw in m.lower() and not any(v in m.lower() for v in ["vision", "vl", "moondream"]):
                return m

    # Fallback to the first available installed model
    return installed[0]


async def get_best_available_model(
    requested_model: Optional[str] = None,
    installed: Optional[List[str]] = None
) -> Optional[str]:
    """
    Asynchronously resolves the optimal Ollama model to use.
    If requested_model is installed, returns it.
    Otherwise returns the best installed chat/text model, or None if no models installed.
    """
    if installed is None:
        installed = await get_installed_models()
    if not installed:
        return None

    if requested_model:
        req_clean = requested_model.lower().strip()
        if not req_clean.startswith(("groq", "gemini", "openai", "claude")):
            req_base = req_clean.split(":")[0]
            for m in installed:
                m_lower = m.lower()
                m_base = m_lower.split(":")[0]
                if req_clean == m_lower or req_base == m_base or req_base in m_lower or m_base in req_base:
                    return m

    for candidate_kw in ["qwen2.5-coder", "qwen2.5", "qwen", "llama3.2", "llama3.1", "llama3", "llama", "mistral", "phi3", "phi", "gemma"]:
        for m in installed:
            if candidate_kw in m.lower() and not any(v in m.lower() for v in ["vision", "vl", "moondream"]):
                return m

    return installed[0]


async def check_model_availability(target_model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """Check if Ollama is running and whether a compatible model is installed."""
    host = await get_working_ollama_host()
    if not host:
        return {
            "ollama_running": False,
            "target_model": target_model,
            "model_installed": False,
            "installed_models": [],
            "message": "Ollama service is not running on 127.0.0.1:11434"
        }

    installed = await get_installed_models()
    best_model = await get_best_available_model(target_model, installed)
    is_installed = best_model is not None
    active_model = best_model or target_model

    return {
        "ollama_running": True,
        "target_model": active_model,
        "model_installed": is_installed,
        "installed_models": installed,
        "message": f"Local model '{active_model}' is ready." if is_installed else "No local AI models installed in Ollama. Install a model to enable offline chat."
    }


async def stream_pull_model(model_name: str = DEFAULT_MODEL) -> AsyncGenerator[str, None]:
    """Stream model download progress from Ollama /api/pull endpoint as SSE line objects."""
    host = await get_working_ollama_host() or "http://127.0.0.1:11434"
    url = f"{host}/api/pull"
    payload = {"name": model_name, "stream": True}

    logger.info(f"Initiating auto-pull for Ollama model '{model_name}' on {host}...")
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    yield json.dumps({"status": "error", "message": f"HTTP {response.status_code} from Ollama"}) + "\n"
                    return

                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            status = data.get("status", "")
                            completed = data.get("completed", 0)
                            total = data.get("total", 0)

                            percent = 0.0
                            if total > 0:
                                percent = round((completed / total) * 100, 1)

                            out = {
                                "status": status,
                                "completed": completed,
                                "total": total,
                                "percent": percent,
                                "model": model_name
                            }
                            yield json.dumps(out) + "\n"
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        logger.error(f"Error during Ollama model pull: {e}")
        yield json.dumps({"status": "error", "message": str(e)}) + "\n"


_ACTIVE_HARDWARE_MODE: str = "cpu"


def get_system_hardware_specs() -> Dict[str, Any]:
    """
    Retrieve detailed hardware specs including CPU threads, RAM (GB),
    and verified GPU compute access (CUDA / ROCm) with reasons for UI toggles.
    """
    import psutil
    import platform
    global _ACTIVE_HARDWARE_MODE
    
    cpu_threads = os.cpu_count() or 8
    try:
        ram_bytes = psutil.virtual_memory().total
        ram_gb = round(ram_bytes / (1024 ** 3), 1)
    except Exception:
        ram_gb = 16.0

    gpu_name = "Integrated / CPU"
    vram_gb = 0.0
    has_gpu_access = False
    cuda_available = False
    gpu_reason = "No dedicated GPU detected. Operating on CPU parallel multi-threaded engine."
    hardware_adapter_name = ""

    # 1. First check if a physical graphics adapter exists on Windows
    if platform.system() == "Windows":
        try:
            import subprocess
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"],
                text=True, stderr=subprocess.DEVNULL, timeout=2.0
            ).strip()
            if out:
                adapters = [line.strip() for line in out.splitlines() if line.strip()]
                if adapters:
                    hardware_adapter_name = adapters[0]
                    gpu_name = hardware_adapter_name
        except Exception:
            pass

    # 2. Verify actual compute acceleration capability (PyTorch CUDA)
    try:
        import torch
        if torch.cuda.is_available() and torch.cuda.device_count() > 0:
            cuda_available = True
            has_gpu_access = True
            gpu_name = torch.cuda.get_device_name(0)
            vram_bytes = torch.cuda.get_device_properties(0).total_memory
            vram_gb = round(vram_bytes / (1024 ** 3), 1)
            gpu_reason = f"High-speed CUDA compute active on {gpu_name} ({vram_gb} GB VRAM)."
        else:
            if hardware_adapter_name:
                if any(x in hardware_adapter_name.lower() for x in ["nvidia", "geforce", "rtx", "gtx"]):
                    gpu_reason = f"NVIDIA GPU ({hardware_adapter_name}) detected, but PyTorch CUDA compute libraries are not installed. Reinstall torch with CUDA support to enable."
                else:
                    gpu_reason = f"{hardware_adapter_name} detected, but lacks CUDA compute runtime. GPU switch disabled to avoid crashes."
            else:
                gpu_reason = "No compatible CUDA/ROCm GPU compute device detected on this laptop."
    except Exception as e:
        gpu_reason = f"GPU compute detection error: {e}"

    if not has_gpu_access and _ACTIVE_HARDWARE_MODE == "gpu":
        _ACTIVE_HARDWARE_MODE = "cpu"

    return {
        "cpu_threads": cpu_threads,
        "ram_gb": ram_gb,
        "gpu_name": gpu_name,
        "vram_gb": vram_gb,
        "has_gpu": has_gpu_access,
        "has_gpu_access": has_gpu_access,
        "cuda_available": cuda_available,
        "hardware_adapter_name": hardware_adapter_name or gpu_name,
        "gpu_disabled_reason": gpu_reason if not has_gpu_access else "",
        "acceleration_mode": "GPU AUTO-ACCELERATED" if (_ACTIVE_HARDWARE_MODE == "gpu" and has_gpu_access) else "CPU PARALLEL ENGINE",
        "active_mode": _ACTIVE_HARDWARE_MODE if has_gpu_access else "cpu",
        "os": platform.system(),
        "arch": platform.machine(),
    }


def set_active_hardware_mode(mode: str) -> Dict[str, Any]:
    """Update global hardware mode."""
    global _ACTIVE_HARDWARE_MODE
    mode = mode.lower().strip()
    specs = get_system_hardware_specs()
    if mode == "gpu" and not specs.get("has_gpu_access", False):
        _ACTIVE_HARDWARE_MODE = "cpu"
        return {
            "success": False,
            "mode": "cpu",
            "message": specs.get("gpu_disabled_reason", "GPU compute not available.")
        }
    _ACTIVE_HARDWARE_MODE = mode
    return {
        "success": True,
        "mode": _ACTIVE_HARDWARE_MODE,
        "message": f"Active mode set to {_ACTIVE_HARDWARE_MODE.upper()}"
    }


