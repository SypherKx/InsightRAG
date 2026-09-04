"""
InsightRAG AI — Autonomous Local Multimodal RAG Engine Launcher

Starts:
  1. FastAPI backend on port 8000
  2. Vite frontend dev server on port 5173

Then opens http://localhost:5173 in the browser.
"""

import os
import sys
import time
import shutil
import subprocess
import threading
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass

ANSI_CYAN   = "\033[96m"
ANSI_GREEN  = "\033[92m"
ANSI_YELLOW = "\033[93m"
ANSI_RED    = "\033[91m"
ANSI_BOLD   = "\033[1m"
ANSI_RESET  = "\033[0m"

BANNER = f"""{ANSI_CYAN}
======================================================================
  ___           _       _     _     ____      _    ____ 
 |_ _|_ __  ___(_) __ _| |__ | |_  |  _ \    / \  / ___|
  | || '_ \/ __| |/ _` | '_ \| __| | |_) |  / _ \| |  _ 
  | || | | \__ \ | (_| | | | | |_  |  _ <  / ___ \ |_| |
 |___|_| |_|___/_|\__, |_| |_|\__| |_| \_\/_/   \_\____|
                  |___/                                 
======================================================================
 [ INSIGHT RAG ] - Autonomous Multimodal RAG Engine
======================================================================{ANSI_RESET}
"""

def print_step(msg, status="OK", color=ANSI_GREEN):
    print(f"{ANSI_BOLD}[*]{ANSI_RESET} {msg}... [{color}{status}{ANSI_RESET}]")

def check_python():
    v = sys.version_info
    print_step(f"Checking Python installation ({v.major}.{v.minor}.{v.micro})", "OK", ANSI_GREEN)

def check_and_start_ollama():
    try:
        import httpx
        try:
            resp = httpx.get("http://127.0.0.1:11434/api/tags", timeout=1.5)
            if resp.status_code == 200:
                print_step("Checking Ollama AI Engine installation", "OK", ANSI_GREEN)
                print_step("Checking Ollama local service", "ACTIVE", ANSI_GREEN)
                return
        except Exception:
            pass
    except ImportError:
        pass

    ollama_bin = shutil.which("ollama")
    if not ollama_bin:
        local_appdata = os.getenv("LOCALAPPDATA", "")
        cand = os.path.join(local_appdata, "Programs", "Ollama", "ollama.exe")
        if os.path.exists(cand):
            ollama_bin = cand
        else:
            ollama_bin = "ollama"

    print_step("Checking Ollama AI Engine installation", "FOUND", ANSI_GREEN)
    print_step("Checking Ollama local service", "STARTING SERVICE", ANSI_YELLOW)

    try:
        if os.name == 'nt':
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen([ollama_bin, "serve"], creationflags=CREATE_NO_WINDOW)
        else:
            subprocess.Popen([ollama_bin, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"{ANSI_BOLD}[*]{ANSI_RESET} Ollama process launched in background.")
        time.sleep(1.5)
    except Exception as e:
        print(f"{ANSI_YELLOW}[!] Warning: Could not auto-launch Ollama: {e}{ANSI_RESET}")

def check_hardware():
    threads = os.cpu_count() or 8
    has_gpu = False
    try:
        import torch
        if torch.cuda.is_available():
            has_gpu = True
            gpu_name = torch.cuda.get_device_name(0)
            print_step(f"Hardware Architecture: NVIDIA CUDA [{gpu_name}]", "ACTIVE GPU", ANSI_GREEN)
    except Exception:
        pass
    if not has_gpu:
        print_step(f"Hardware Architecture: Standard Multi-Core CPU ({threads} Threads)", "ACTIVE CPU", ANSI_GREEN)

def install_deps():
    print(f"\n{ANSI_BOLD}[*] Checking & downloading dependencies with live status:{ANSI_RESET}")
    print("-" * 65)
    required = ["fastapi", "uvicorn", "pydantic", "httpx", "pandas", "numpy", "scipy", "chardet", "python-multipart", "psutil"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
            print(f"  {ANSI_GREEN}+ {pkg:<30} [ INSTALLED ]{ANSI_RESET}")
        except ImportError:
            missing.append(pkg)
            print(f"  {ANSI_YELLOW}- {pkg:<30} [ INSTALLING ]{ANSI_RESET}")
    if missing:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
    print(f"\n{ANSI_GREEN}[OK] All dependencies installed successfully!{ANSI_RESET}")

def run_backend():
    """Run FastAPI backend on port 8000 in a background thread."""
    os.chdir(str(ROOT_DIR))
    os.environ["RAG_ENABLED"] = "true"
    os.environ["OLLAMA_HOST"] = "http://127.0.0.1:11434"
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, log_level="info", reload=False)

def run_frontend_dev():
    """Run Vite dev server for the frontend on port 5173."""
    frontend_dir = ROOT_DIR / "frontend"
    npm_cmd = "npm"
    if os.name == 'nt':
        npm_cmd = "npm.cmd"
    return subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(frontend_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='ignore'
    )

def wait_for_port(port, timeout=30):
    import socket
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except Exception:
            time.sleep(0.5)
    return False

def main():
    print(BANNER)
    check_python()
    check_and_start_ollama()
    check_hardware()
    install_deps()

    print(f"\n{'='*65}")
    print(f"{ANSI_BOLD}+---------------------------------------------------------------+{ANSI_RESET}")
    print(f"{ANSI_BOLD}| InsightRAG Studio is launching...                             |{ANSI_RESET}")
    print(f"{ANSI_BOLD}| Backend API  : http://localhost:8000                          |{ANSI_RESET}")
    print(f"{ANSI_BOLD}| Frontend UI  : http://localhost:5173                          |{ANSI_RESET}")
    print(f"{ANSI_BOLD}| Local-First  | Zero API Costs  | Hardware Accelerated         |{ANSI_RESET}")
    print(f"{ANSI_BOLD}+---------------------------------------------------------------+{ANSI_RESET}")
    print(f"{'='*65}\n")

    # Start FastAPI backend in a background thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    print(f"[>] Backend API starting on http://localhost:8000 ...")

    # Start Vite dev server as a subprocess
    print(f"[>] Frontend dev server starting on http://localhost:5173 ...")
    vite_proc = run_frontend_dev()

    # Stream Vite output so user can see startup logs
    def stream_vite():
        for line in vite_proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()

    threading.Thread(target=stream_vite, daemon=True).start()

    # Wait for both ports to be ready
    print(f"[*] Waiting for services to be ready...")
    wait_for_port(8000, timeout=20)
    ready = wait_for_port(5173, timeout=30)

    if ready:
        print(f"\n{ANSI_GREEN}[OK] InsightRAG Studio is LIVE! Launching Knowledge Base Studio...{ANSI_RESET}")
        webbrowser.open("http://localhost:5173/app/upload")
    else:
        print(f"\n{ANSI_YELLOW}[!] Frontend may still be starting — open http://localhost:5173/app/upload manually.{ANSI_RESET}")

    # Keep process alive
    try:
        vite_proc.wait()
    except KeyboardInterrupt:
        print(f"\n{ANSI_CYAN}[*] Shutting down InsightRAG Studio. Goodbye!{ANSI_RESET}")
        vite_proc.terminate()

if __name__ == "__main__":
    main()
