<div align="center">

# ⚡ INSIGHT • RAG
### 🧠 Universal Multimodal Document Intelligence & RAG Factory
**Zero-Budget • 100% On-Device Vector Privacy • Hardware Auto-Tuned • Multimodal Vision & ROI Diagram Cropping**

<br />
<pre align="center">
██╗███╗   ██╗███████╗██╗ ██████╗ ██╗  ██╗████████╗    ██████╗   █████╗   ██████╗ 
██║████╗  ██║██╔════╝██║██╔════╝ ██║  ██║╚══██╔══╝    ██╔══██╗ ██╔══██╗ ██╔════╝ 
██║██╔██╗ ██║███████╗██║██║  ███╗███████║   ██║       ██████╔╝ ███████║ ██║  ███╗
██║██║╚██╗██║╚════██║██║██║   ██║██╔══██║   ██║       ██╔══██╗ ██╔══██║ ██║   ██║
██║██║ ╚████║███████║██║╚██████╔╝██║  ██║   ██║       ██║  ██║ ██║  ██║ ╚██████╔╝
╚═╝╚═╝  ╚═══╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝       ╚═╝  ╚═╝ ╚═╝  ╚═╝  ╚═════╝ 
</pre>

<br />

<p align="center">
  <a href="#-1-line-quickstart"><b>⚡ Quickstart</b></a> •
  <a href="#-key-capabilities--features"><b>🌟 Capabilities</b></a> •
  <a href="#-enterprise-security-hardening"><b>🛡️ Security & Hardening</b></a> •
  <a href="#%EF%B8%8F-system-architecture"><b>🏗️ Architecture</b></a> •
  <a href="https://github.com/SypherKx/InsightRAG"><b>💻 GitHub Repo</b></a>
</p>

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-7-646CFF.svg?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev)
[![FAISS](https://img.shields.io/badge/FAISS-CPU%20VectorStore-blue.svg?style=for-the-badge)](https://github.com/facebookresearch/faiss)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-black.svg?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.com)
[![Vision LLM](https://img.shields.io/badge/Vision%20LLM-Moondream%20%7C%20Qwen2.5--VL-ff69b4.svg?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.com)
[![OCR](https://img.shields.io/badge/OCR-RapidOCR%20Fallback-orange.svg?style=for-the-badge)](https://github.com/RapidAI/RapidOCR)
[![License: MIT](https://img.shields.io/badge/License-MIT-FEE75C.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

<br />
<br />

![InsightRAG AI — Universal Multimodal RAG Factory](./docs/assets/insightrag_hero_banner.png)

</div>

---

## 📖 Overview

**InsightRAG AI** is an autonomous, universal multimodal Retrieval-Augmented Generation (RAG) platform. It converts complex PDF manuals, technical blueprints, scientific papers, textbooks, and enterprise data into an interactive, grounded AI knowledge studio in seconds — **with 100% on-device data privacy, zero mandatory API bills, and enterprise-grade security**.

---

## ⚡ 1-Line Quickstart

### 🪟 Windows (Universal 1-Line - Run from ANY Terminal / Directory)
Open **PowerShell** (no need to `cd` or navigate to any folder) and run:

```powershell
irm https://www.insightrag.tech/install.ps1 | iex
```

> [!TIP]
> ### ⚡ Subsequent Launches (100% Offline — No Internet Needed!)
> Once downloaded/installed, you **never need an active internet connection** or to re-run the web installer. Simply open **any PowerShell or Command Prompt** window and run:
> ```powershell
> insightrag
> ```
> **And you're good to go!** It will immediately boot all local AI pipelines and open your browser offline.

### 🖱️ 1-Click Double-Click (Local Folder)
If you downloaded/cloned the repository locally, simply double-click:
👉 **`run.bat`** in the project folder!

*What happens automatically in seconds:*
1. 🔍 **Zero-Friction Detection**: Automatically finds or sets up the project environment.
2. ⚡ **Hardware Profiling**: Detects CPU cores, RAM, and NVIDIA CUDA GPU.
3. 📦 **Self-Healing Dependencies**: Auto-verifies and installs Python + Node.js packages.
4. 🤖 **Ollama Auto-Start**: Starts local AI engine in the background.
5. 🚀 **Auto-Opens Browser**: Cleans ports and directly opens the **Live Studio** at `http://localhost:5173/app/upload`!

---

### 🐧 Linux / macOS / Manual Python Launch

```bash
# 1. Clone the repository
git clone https://github.com/SypherKx/InsightRAG.git
cd InsightRAG

# 2. Run the automated local runner
python scripts/run_local.py
```

---

## 🌟 Key Capabilities & Features

### 1. 👁️ Native Vision LLM (Moondream & Qwen2.5-VL) + RapidOCR Dual Engine
* **On-Device Vision Intelligence**: Deep visual document comprehension powered natively by lightweight local Vision LLMs (**`moondream:latest`** and **`qwen2.5vl:latest`**) via Ollama.
* **Complex Diagram & Schematic Comprehension**: Understands and reasons over system architectures, electrical schematics, flowcharts, mathematical diagrams, process cycles, and technical blueprints.
* **RapidOCR Resilient Fallback**: If documents contain low-contrast scans, rotated text, or non-searchable images lacking text layers, the pipeline automatically engages an embedded **RapidOCR** engine to extract exact textual symbols and coordinate bounding boxes.

### 2. 🎯 Targeted Visual ROI & Diagram Auto-Cropping & Fingerprinting
* **Intelligent Sub-Region Isolation**: When querying specific components (e.g., *"show me the attention mechanism diagram"* or *"Figure 3 block diagram"*), the engine scans PDF vector graphics (`fitz.get_drawings()`) and image regions to extract only the target visual asset.
* **Perceptual Visual Fingerprinting**: Extracted diagrams and sub-regions are fingerprinted with perceptual hashes (`dhash`, `phash`, MD5), preventing duplicate vectors and binding exact figures to semantic search anchors.
* **Interactive Visual Evidence Cards**: Chat answers render zoomable, high-res visual diagram cards with page attribution, crop previews, and full enlargement on click.

### 3. 🛡️ Factual Shield & Anti-Hallucination Calibration
* **Cosine Distance Gating**: Dynamically calculates semantic distance thresholds against retrieved chunks. If source evidence is weak or missing, the model deterministically triggers a zero-evidence refusal protocol rather than hallucinating answers.
* **HyDE (Hypothetical Document Embeddings)**: Generates hypothetical response vectors to bridge the vocabulary gap between short user questions and dense technical documentation.
* **Strict Source Grounding**: Enforces rigid context boundaries (`<document_context>`) ensuring answers derive exclusively from indexed pages.

### 4. 🔁 RLHF Feedback Store & Adaptive Reranking
* **Interactive Upvote/Downvote Feedback**: Users can rate retrieval responses directly in the studio chat interface.
* **On-Device SQLite Feedback Store**: Stores ratings and queries locally in `feedback_store.py` (`insightforge.db`).
* **Adaptive Reranking**: Automatically boosts highly-rated chunks and penalizes poorly aligned passages on future queries.

### 5. 📦 1-Click Local Model Hub & Background Streaming
* **Zero-Terminal Model Installation**: Pull and switch local LLMs and Vision models (`llama3.2:3b`, `moondream:latest`, `qwen2.5-coder:7b`, `mistral`) directly inside the studio UI.
* **Live SSE Progress Bars**: Real-time layer download percentages, transfer rates, and model verification streamed via Server-Sent Events.

### 6. 🔒 Air-Gapped Terminal Launcher & Studio Gating
* **Single Command Setup**: Run `irm https://www.insightrag.tech/install.ps1 | iex` from any terminal on Windows.
* **Gated Studio Workspace**: Studio is strictly locked until the terminal completes dependency setup and boots the local engine on port 8000, then automatically unlocks the workspace in your browser.
* **Global Offline Command**: Auto-registers `insightrag` command globally across Windows for 100% offline launches without internet.

### 7. 🔬 Deep Page-by-Page Multimodal Ingestion & Analysis
* **Exhaustive Document Comprehension**: Never skims or rushes. Every page is systematically inspected, extracting high-fidelity text, vector graphics, image bounding boxes, tables, and mathematical formulas.
* **Granular Visual Metadata**: Images, figures, and diagrams are tagged with their exact page coordinates (`[x0, y0, x1, y1]`) and embedded into dense vector memory with distinct context anchors.

### 8. 🖥️ Dedicated Fullscreen Chat Studio with Ingestion Gating
* **Two-Phase Workflow**: Documents first undergo thorough multi-stage ingestion with animated progress trackers (Reading Pages → Extracting Graphics → Generating Vectors → Storing in FAISS).
* **Immersive Fullscreen Workspace**: Seamlessly transitions into a dedicated fullscreen chat interface with multi-turn memory, high-res zoomable diagram previews, 1-click copy, and executive formatted markdown rendering.

### 9. 💬 Multi-Turn Conversational Memory (ChatGPT Experience)
* **Full Context Retention**: Seamlessly asks follow-up questions referencing previous answers, facts, and citations across multiple turns.
* **Persistent Sessions**: Real-time auto-synchronization to `localStorage` preserves conversations and diagram evidence even after browser exits or PC reboots.
* **Executive Markdown**: Custom rendered tables, copyable code blocks, and visual diagram badges.

### 10. 📑 Selective Page Range Slicing
* **Precision Ingestion**: Upload 1,000+ page books or manuals and choose exact page ranges (e.g., *Page 45 to 80*) to slice and index only the target chapter.
* **Zero Index Bloat**: Saves vector space and boosts retrieval speed.

### 11. ⚡ Dual Compute Architecture (Local Air-Gapped vs. Turbo Cloud)
* **💻 100% Local Mode [DEFAULT]**: Powered by local Ollama (`llama3.2:3b`, `moondream:latest`, `qwen2.5`) and `faiss-cpu`. Zero data leaves your machine.
* **⚡ Advance Turbo Server**: Accelerated cloud processing using Groq (`llama-3.3-70b-versatile`), Google Gemini (`gemini-1.5-flash`), or OpenAI (`gpt-4o-mini`).

### 12. 🧠 Speed-Tiered Dense Embeddings
* **⚡ `all-MiniLM-L6-v2` (Ultra-Fast 5x • 384-dim)**: CPU-friendly embedding inference for fast laptops.
* **⚖️ `bge-small-en-v1.5` (Balanced 3x • 384-dim)**: Top retrieval accuracy for standard desktop PCs.
* **🧠 `bge-base-en-v1.5` (High Precision • 768-dim)**: SOTA dense semantic capture for research & technical depth.
* **🚀 `nomic-embed-text` (Ollama Native 8K • 768-dim)**: High-context 8,192 token window for large book chapters.

---

## 🛡️ Enterprise Security Hardening

InsightRAG AI is audited and hardened against all major web and LLM vulnerabilities:

| Protection Area | Implementation Details |
| :--- | :--- |
| **OWASP Security Headers** | Built-in middleware appending `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Content-Security-Policy (CSP)`, `X-XSS-Protection`, `Referrer-Policy`, and `Permissions-Policy`. |
| **Path Traversal & LFI Defense** | `sanitize_filename` & `validate_safe_path` prevent directory escape (`../` and `..\\` attacks) across all upload and crop endpoints. |
| **Decompression Bomb Protection** | Pillow `Image.MAX_IMAGE_PIXELS = 25_000_000` and uncompressed XML byte-size limits on `.docx` prevent memory flooding DoS attacks. |
| **Prompt Injection Isolation** | RAG context is encapsulated within strict `<document_context>` and `<user_query>` delimiters with hardened anti-jailbreak directives. |
| **Information Disclosure Safety** | Global exception handler prevents internal server paths, database schemas, or tracebacks from leaking into network/DevTools inspect tabs. |
| **Extension Whitelisting** | Strictly enforces whitelist validation (`.pdf`, `.txt`, `.md`, `.csv`, `.docx`, `.png`, `.jpg`, `.webp`) and rejects dangerous executables (`.exe`, `.sh`, `.php`, `.bat`). |

---

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        InsightRAG AI Pipeline                          │
└────────────────────────────────────────────────────────────────────────┘

 [ Documents / Scans ] ──> [ Multimodal Ingestion ] ──> [ Overlapping Chunker ]
   • PDF Manuals & Books     • PyMuPDF Drawings & Slices  • 500 chars (50 ovlp)
   • Technical Blueprints    • Moondream / Qwen2.5-VL     • Token-Aware Splitting
   • Schematics & Scans      • RapidOCR Fallback Layer
                                                                 │
                                                                 ▼
 [ User Natural Query ]                                 [ Dense Embedding Engine ]
          │                                               • all-MiniLM-L6-v2 (384d)
          ▼                                               • bge-small / bge-base
 [ Multi-Turn Memory ] ──> [ HyDE & Cosine Gating ] ────> • nomic-embed-text (8k)
                               (FAISS IndexFlatIP)               │
                                       │                         ▼
                                       ▼                 [ Vector Knowledge Base ]
                             [ Grounded RAG Prompt ]       • 100% Local FAISS Store
                             • <document_context>          • Visual Perceptual Hashes
                             • <user_query>                • RLHF Feedback Weights
                                       │
                                       ▼
                         [ Local Ollama / Turbo Cloud ]
                           • Vision: moondream / qwen2.5-vl
                           • LLM: llama3.2 / qwen2.5-coder
                           • Turbo: Groq 70B / Gemini / GPT-4o
                                       │
                                       ▼
                       [ Cited Answer + Visual Diagram Card ]
```

---

## 📂 Repository Structure

```
InsightRAG/
├── backend/                      # FastAPI Backend & RAG Engine
│   ├── main.py                   # App entrypoint, OWASP headers & CORS middleware
│   ├── config.py                 # Pydantic configuration & model parameters
│   ├── routers/                  # API routers (rag, datasets, anomalies, system)
│   ├── services/                 # RAG pipeline, embedding loader & Ollama manager
│   ├── storage/                  # SQLite database models & secure file store
│   └── utils/                    # Security utilities (path validation, sanitization)
│
├── frontend/                     # React 19 + Vite 7 Frontend Application
│   ├── src/
│   │   ├── routes/               # TanStack Router pages (/, /docs, /app/upload)
│   │   ├── components/           # Neo-Brutalist design system & studio cards
│   │   ├── services/             # Axios API client & WebSocket handlers
│   │   └── styles.css            # Styling, animations & typography
│   └── package.json              # Frontend dependencies
│
├── src/                          # Core analytical and RAG modules
│   ├── detection/                # Statistical change-point & anomaly detection
│   ├── explainer/                # Prompt generators & context formatting
│   ├── ingestion/                # Document cleaning & format parsers
│   └── rag/                      # FAISS store, Moondream vision, ROI cropper, RLHF
│
├── scripts/                      # Utility & automation scripts
│   ├── run_local.py              # Cross-platform Python local runner
│   └── generate_obsidian_vault.py# Obsidian knowledge graph generator
│
├── launch.ps1                    # 1-Click PowerShell launcher for Windows
├── install.ps1                   # Universal 1-line web installer
├── run.bat                       # 1-Click Windows batch launcher
└── README.md                     # Project documentation
```

---

## 🔌 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Server health check, uptime, and security headers status |
| `POST` | `/api/v1/rag/documents` | Upload & vectorize documents with optional `start_page`/`end_page` |
| `GET` | `/api/v1/rag/documents/{task_id}/status` | Check real-time ingestion status and progress |
| `POST` | `/api/v1/rag/query` | Grounded multi-turn RAG query with citations & visual snippet |
| `POST` | `/api/v1/rag/query/stream` | Real-time SSE token streaming query response |
| `GET` | `/api/v1/rag/crop` | Dynamic sub-region diagram cropping and high-resolution rendering |
| `GET` | `/api/v1/rag/images/{doc}/{img}` | Serves extracted visual diagrams and bounding-box image assets |
| `POST` | `/api/v1/rag/feedback` | Upvote/downvote RLHF response feedback for adaptive reranking |
| `GET` | `/api/v1/rag/stats` | Retrieve indexed document vectors and file statistics |
| `POST` | `/api/v1/rag/clear` | Securely purge all documents and vector indices |
| `GET` | `/api/v1/system/specs` | Hardware profiling (CPU cores, RAM, CUDA GPU acceleration) |
| `POST` | `/api/v1/system/hardware-mode` | Dynamic toggle between CPU and CUDA GPU acceleration |
| `POST` | `/api/v1/system/pull-model` | 1-Click Ollama model downloader with live SSE layer progress |
| `GET` | `/api/v1/system/models` | List installed Ollama models on the local device |

---

## 🛠️ Environment Configuration

Create a `.env` file in the project root (optional):

```env
# RAG Configuration
RAG_ENABLED=true
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Local LLM (Ollama)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
LLM_MODEL=llama3.2:3b

# Optional: Cloud Accelerated Keys
GROQ_API_KEY=
GEMINI_API_KEY=
OPENAI_API_KEY=
```

---

## 👤 Author & Credits

Designed and built with ❤️ by **[Karan Pratap Singh](https://github.com/SypherKx)**.

Contributions and pull requests are welcome! If you find InsightRAG helpful, please star ⭐ the repository.
