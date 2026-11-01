# 🛠️ InsightRAG — Operational & Utility Scripts

Automation, benchmarking, and launcher utilities.

---

## 🧭 Scripts Directory Map

| Script | Purpose | How to Run |
|---|---|---|
| **`run_local.py`** | **Master Local Launcher**: Profiles hardware (CPU/RAM/GPU), auto-starts Ollama, boots FastAPI (port 8000) and Vite dev server (port 5173), and opens the browser. | `python scripts/run_local.py` |
| **`benchmark_rag.py`** | Measures vector retrieval latency, chunking throughput, and embedding speeds across CPU and CUDA GPU modes. | `python scripts/benchmark_rag.py` |
| **`generate_obsidian_vault.py`** | Automatically converts indexed documents, anomalies, and insights into an interactive, linked Obsidian Markdown vault. | `python scripts/generate_obsidian_vault.py` |
| **`generate_pdf_report.py`** | Compiles executive PDF intelligence reports from detected anomalies and RAG findings. | `python scripts/generate_pdf_report.py` |
| **`print_banner.py`** | Terminal helper displaying the signature bold cyan ASCII art banner. | `python scripts/print_banner.py` |

