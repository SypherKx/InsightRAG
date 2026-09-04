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
        "C:\\Users\\itska\\AppData\\Local\\Programs\\Ollama\\ollama.exe",
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
    
    # Check if ANY model is installed, or specifically matching target/llama
    is_installed = False
    active_model = target_model

    if installed:
        # 1. Exact or prefix match with target_model
        target_base = target_model.split(':')[0]
        for m in installed:
            if target_model in m or target_base in m or m.startswith(target_base):
                is_installed = True
                active_model = m
                break
        
        # 2. If target model not exact match, pick ANY llama or first available model!
        if not is_installed:
            llama_models = [m for m in installed if "llama" in m.lower()]
            if llama_models:
                is_installed = True
                active_model = llama_models[0]
            else:
                is_installed = True
                active_model = installed[0]

    return {
        "ollama_running": True,
        "target_model": active_model,
        "model_installed": is_installed,
        "installed_models": installed,
        "message": f"Local model '{active_model}' is ready." if is_installed else "No model found. Click to pull llama3.2."
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


def get_system_hardware_specs() -> Dict[str, Any]:
    """Retrieve detailed hardware specs including CPU threads, RAM (GB), and CUDA/GPU status."""
    import psutil
    import platform
    
    cpu_threads = os.cpu_count() or 8
    try:
        ram_bytes = psutil.virtual_memory().total
        ram_gb = round(ram_bytes / (1024 ** 3), 1)
    except Exception:
        ram_gb = 16.0

    gpu_name = "Integrated / CPU"
    vram_gb = 0.0
    has_gpu = False
    acceleration_mode = "CPU PARALLEL ENGINE"

    try:
        import torch
        if torch.cuda.is_available():
            has_gpu = True
            gpu_name = torch.cuda.get_device_name(0)
            vram_bytes = torch.cuda.get_device_properties(0).total_memory
            vram_gb = round(vram_bytes / (1024 ** 3), 1)
            acceleration_mode = "GPU AUTO-ACCELERATED"
    except Exception:
        pass

    return {
        "cpu_threads": cpu_threads,
        "ram_gb": ram_gb,
        "gpu_name": gpu_name,
        "vram_gb": vram_gb,
        "has_gpu": has_gpu,
        "acceleration_mode": acceleration_mode,
        "os": platform.system(),
        "arch": platform.machine(),
    }

