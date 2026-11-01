# ⚡ InsightRAG — Backend Architecture & Developer Guide

FastAPI-powered asynchronous backend server for InsightRAG AI.

---

## 🧭 Directory Map

```
backend/
├── main.py               # 🚀 Entrypoint: FastAPI app, lifespan, CORS, OWASP headers & SPA mount
├── config.py             # ⚙️ Settings: Pydantic environment configuration (LLMs, ports, DB, admins)
├── dependencies.py       # 💉 Dependency Injection: FileStore, RAGService, AnalysisService singletons
├── requirements.txt      # 📦 Python backend & ML package dependencies
│
├── models/               # 📋 Pydantic Schemas & Data Contracts
│   ├── requests.py       # Input validation for RAG queries, feedback, models
│   └── responses.py      # Standardized JSON response envelopes
│
├── routers/              # 🌐 HTTP API Controllers (/api/v1)
│   ├── auth.py           # User sign-in audit logs, activity tracking & admin viewer
│   ├── rag.py            # Document ingestion, FAISS queries, SSE streaming & diagram cropping
│   ├── datasets.py       # CSV/TSV parsing, schema validation & upload handling
│   ├── anomalies.py      # Anomaly discovery & statistical rankings
│   ├── system.py         # Hardware detection (CPU/CUDA GPU), Ollama model management
│   └── health.py         # Uptime & security headers check
│
├── services/             # ⚙️ Core Business Logic
│   ├── rag_service.py    # Bridges FastAPI with FAISS vector store & LLM generator
│   ├── dataset_service.py# File normalization, schema inference & quality scores
│   └── analysis.py       # Root-cause analysis & natural language generation
│
├── storage/              # 💾 Data Layer
│   ├── database.py       # SQLAlchemy ORM models (datasets, anomalies, user_access_logs)
│   └── file_store.py     # Local disk file storage & path resolution
│
└── utils/                # 🛡️ Security & Authentication Utilities
    ├── firebase_auth.py  # Firebase Admin token verification & admin RBAC check
    ├── rate_limiter.py   # Sliding-window in-memory anti-DoS & brute-force rate limiter
    └── security.py       # Path traversal validation & safe filename sanitization
```

---

## 🚀 Key Workflows

### 1. Authentication & Security Flow
1. **Token Ingestion**: Incoming requests with `Authorization: Bearer <firebase_id_token>` are decoded by [`firebase_auth.py`](utils/firebase_auth.py).
2. **Admin Validation**: Endpoints like `GET /api/v1/auth/logs` invoke `require_admin` to restrict access strictly to whitelisted admin emails in [`config.py`](config.py).
3. **Audit Logging**: Every login, dataset upload, and RAG query creates an entry in `user_access_logs` in SQLite via [`database.py`](storage/database.py).

### 2. RAG Execution Flow
1. User submits a query to `POST /api/v1/rag/query`.
2. Router forwards request to [`rag_service.py`](services/rag_service.py), which interfaces with the core engine in `src/rag/`.
3. Embeddings are generated via Sentence-Transformers / Ollama, queried against the local FAISS index, filtered by cosine gating (anti-hallucination), and synthesized by Ollama / Groq / OpenAI.

---

## 🛠️ Running Locally (Standalone)

```bash
# From workspace root:
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be live at: **`http://127.0.0.1:8000/docs`**

