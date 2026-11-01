# 🧠 InsightRAG — Core AI & Analytics Engine (`src/`)

Python library containing all algorithmic pipelines, multimodal vision extraction, dense vector embeddings, and statistical anomaly detection.

---

## 🧭 Directory Map

```
src/
├── rag/                  # 🔍 Multimodal RAG Pipeline
│   ├── chunker.py        # Token-aware sliding chunker with configurable overlap
│   ├── embeddings.py     # Dense embeddings (all-MiniLM, BGE, Nomic-Embed)
│   ├── vectorstore.py    # 100% on-device FAISS vector indexer & serialization
│   ├── image_regions.py  # Visual ROI diagram cropper & perceptual visual hashes
│   ├── anti_hallucination.py # Cosine distance gating & factual grounding shield
│   ├── feedback_store.py # Local SQLite RLHF upvote/downvote store for reranking
│   ├── retriever.py      # Hybrid dense + lexical retrieval coordinator
│   └── pipeline.py       # End-to-end RAG workflow orchestration
│
├── ingestion/            # 📄 Multi-Format Document Ingestion
│   ├── parser.py         # Extracts text & drawings from PDF, DOCX, CSV, TXT
│   ├── cleaner.py        # Unicode repair, whitespace normalization & cleaning
│   ├── validator.py      # File structure, schema integrity & safety validation
│   └── storage.py        # Processed document persistence & metadata store
│
├── detection/            # 📊 Statistical Anomaly Detection
│   ├── algorithms.py     # Z-Score, IQR, Isolation Forest & STL decomposition
│   ├── detector.py       # Multi-algorithm anomaly discovery engine
│   └── scorer.py         # Severity & confidence ranking algorithms
│
├── root_cause/           # 🎯 Root-Cause Attribution Engine
│   ├── analyzer.py       # Driver analysis & multi-variable attribution
│   ├── correlator.py     # Pearson & Spearman correlation matrices
│   └── segmenter.py      # High-dimensional slicing & change-point locator
│
└── explainer/            # 💬 Natural Language Insights
    ├── generator.py      # Structured natural language summary & prompt builder
    └── llm_client.py     # Multi-provider client (Ollama, Groq, OpenAI)
```

---

## 🔗 How It Interacts With `backend/`
- When FastAPI receives a request (e.g. `/api/v1/rag/query`), it calls [`backend/services/rag_service.py`](../backend/services/rag_service.py).
- `rag_service.py` directly delegates heavy computation to `src/rag/pipeline.py` and `src/rag/retriever.py`.
- This clean separation allows `src/` to be imported as an independent Python library or tested in CLI scripts without running a web server.

