import os
import re
import json
import shutil
from pathlib import Path

# Detect base directory
SCRIPT_DIR = Path(__file__).parent.resolve()
BASE_DIR = SCRIPT_DIR.parent.resolve()

VAULT_DIR = BASE_DIR / "obsidian_vault"
FILES_DIR = VAULT_DIR / "files"
OBSIDIAN_DIR = VAULT_DIR / ".obsidian"

def reset_vault():
    """Wipes old vault to eliminate leftover orphan notes and clutter."""
    if VAULT_DIR.exists():
        shutil.rmtree(VAULT_DIR)
    os.makedirs(FILES_DIR, exist_ok=True)
    os.makedirs(OBSIDIAN_DIR, exist_ok=True)

def write_obsidian_graph_config():
    """Configures Obsidian Graph View to hide orphans, scale nodes, and color-code clusters cleanly."""
    graph_config = {
        "collapse-filter": False,
        "search": "",
        "showTags": True,
        "showAttachments": False,
        "hideUnresolved": True,
        "showOrphans": False,
        "collapse-color-groups": False,
        "colorGroups": [
            {"query": "tag:#hub", "color": {"a": 1, "rgb": 16711807}},       # Neon Pink/Magenta
            {"query": "tag:#rag", "color": {"a": 1, "rgb": 62463}},          # Bright Cyan
            {"query": "tag:#anomaly", "color": {"a": 1, "rgb": 57250}},       # Emerald Green
            {"query": "tag:#rootcause", "color": {"a": 1, "rgb": 16758784}}, # Gold/Amber
            {"query": "tag:#backend", "color": {"a": 1, "rgb": 5195493}},    # Royal Blue
            {"query": "tag:#frontend", "color": {"a": 1, "rgb": 16730199}},   # Coral Red
            {"query": "tag:#database", "color": {"a": 1, "rgb": 7381503}}     # Deep Indigo
        ],
        "collapse-display": False,
        "showArrow": True,
        "textScale": 1.2,
        "showLabels": True,
        "linkThickness": 2.0,
        "nodeSize": 2.8,
        "collapse-forces": False,
        "centerStrength": 0.45,
        "repelStrength": 16.5,
        "linkStrength": 1.2,
        "linkDistance": 130
    }
    
    with open(OBSIDIAN_DIR / "graph.json", "w", encoding="utf-8") as f:
        json.dump(graph_config, f, indent=2)

def clean_note_id(filepath):
    s = str(filepath).replace("\\", "_").replace("/", "_").replace(".", "_")
    return s

def build_core_hub_notes():
    index_content = """---
tags:
  - #hub
  - #architecture
---
# 🧠 InsightRAG AI — Master System Graph

> **Welcome to the Central Navigation Hub**. This graph maps out all core subsystems of InsightRAG AI. Click any node or link below to navigate the project architecture.

---

## 🏛️ Subsystem Maps (MOC Hubs)

- [[01_System_Architecture]] — End-to-end data flow & tech stack blueprint.
- [[02_RAG_Pipeline_Hub]] — Document ingestion, chunking, embeddings, FAISS vector database & Groq LLM context synthesis.
- [[03_Statistical_Anomaly_Hub]] — Multi-algorithm clinical vital anomaly detection (Z-score, MAD, IQR, Pettitt change-point test).
- [[04_Root_Cause_Engine_Hub]] — Dimension attribution, segmenter, and correlation analyzer.
- [[05_FastAPI_Backend_Hub]] — Backend REST routes, database models, dependency injection & storage services.
- [[06_Frontend_App_Hub]] — React / TanStack Router dashboard views, API client hooks & UI state management.

---

## 🎨 Graph Color Legend

- 💖 **`#hub`** — Core Subsystem Architectures
- 🩵 **`#rag`** — Vector Search & RAG Pipeline
- 💚 **`#anomaly`** — Statistical Anomaly Algorithms
- 💛 **`#rootcause`** — Protocol Root-Cause Analysis
- 💙 **`#backend`** — FastAPI Routers & Services
- ❤️ **`#frontend`** — React Dashboard Views & API Hooks
- 💜 **`#database`** — SQLite & FAISS Persistence
"""
    with open(VAULT_DIR / "00_Master_Hub.md", "w", encoding="utf-8") as f:
        f.write(index_content)

    arch_content = """---
tags:
  - #hub
  - #architecture
---
# 🏛️ 01 System Architecture

> **Master Hub**: [[00_Master_Hub]]

---

## 🔄 End-to-End Subsystem Connections

```mermaid
graph TD
    Client[React Frontend] -->|REST API| Backend[FastAPI Backend]
    
    subgraph RAG System
        Backend --> RAG[RAG Pipeline Orchestrator]
        RAG --> Ingestion[Document Ingestion]
        RAG --> Chunker[Text Chunker]
        RAG --> Embeddings[HuggingFace Embeddings]
        RAG --> FAISS[FAISS Vector Store]
        RAG --> Groq[Groq LLM Client]
    end

    subgraph Anomaly System
        Backend --> Anomaly[Anomaly Detector]
        Anomaly --> Algorithms[Z-Score / MAD / IQR / Pettitt]
        Anomaly --> Scorer[Ensemble Scorer]
        Anomaly --> RootCause[Root Cause Analyzer]
    end

    subgraph Persistence
        Backend --> DB[(SQLite Database)]
        FAISS --> DiskIndex[FAISS Vector Files]
    end
```

---

## 🔗 Direct Links to Subsystem Hubs

- [[02_RAG_Pipeline_Hub]]
- [[03_Statistical_Anomaly_Hub]]
- [[04_Root_Cause_Engine_Hub]]
- [[05_FastAPI_Backend_Hub]]
- [[06_Frontend_App_Hub]]
"""
    with open(VAULT_DIR / "01_System_Architecture.md", "w", encoding="utf-8") as f:
        f.write(arch_content)

    rag_content = """---
tags:
  - #hub
  - #rag
---
# 🩵 02 RAG Pipeline Subsystem Hub

> **Master Hub**: [[00_Master_Hub]] | **Architecture**: [[01_System_Architecture]]

---

## 🎯 Core RAG Pipeline Modules

- [[files/src_rag_pipeline_py]] — Central RAG Orchestrator (`RAGPipeline`).
- [[files/src_rag_ingestion_py]] — PDF/CSV/MD File Ingester.
- [[files/src_rag_chunker_py]] — Text Chunking engine (500 chars, 50 overlap).
- [[files/src_rag_embeddings_py]] — Dense Vector Generator (`all-MiniLM-L6-v2`).
- [[files/src_rag_vectorstore_py]] — FAISS CPU Vector Index (`IndexFlatIP`).
- [[files/src_rag_retriever_py]] — Top-K Context Retriever.
- [[files/src_rag_models_py]] — Dataclasses for Document & Chunk objects.

---

## ⚡ Data Flow Connections
- Connected Backend Routers: [[files/backend_routers_rag_py]] & [[files/backend_services_rag_service_py]]
"""
    with open(VAULT_DIR / "02_RAG_Pipeline_Hub.md", "w", encoding="utf-8") as f:
        f.write(rag_content)

    anomaly_content = """---
tags:
  - #hub
  - #anomaly
---
# 💚 03 Statistical Anomaly Engine Hub

> **Master Hub**: [[00_Master_Hub]] | **Architecture**: [[01_System_Architecture]]

---

## 🧮 Core Anomaly Modules

- [[files/src_detection_detector_py]] — Anomaly Detector Orchestrator (`AnomalyDetector`).
- [[files/src_detection_algorithms_py]] — Algorithms implementation (Z-Score, MAD, IQR, Pettitt Test).
- [[files/src_detection_scorer_py]] — Anomaly severity & ensemble scoring.
- [[files/src_detection_models_py]] — Data models for raw signals & anomaly alerts.

---

## ⚡ Connected Backend Routes
- Connected Backend Routers: [[files/backend_routers_anomalies_py]] & [[files/backend_services_analysis_py]]
"""
    with open(VAULT_DIR / "03_Statistical_Anomaly_Hub.md", "w", encoding="utf-8") as f:
        f.write(anomaly_content)

    rc_content = """---
tags:
  - #hub
  - #rootcause
---
# 💛 04 Root Cause Engine Hub

> **Master Hub**: [[00_Master_Hub]] | **Architecture**: [[01_System_Architecture]]

---

## 🔍 Root Cause Analysis Modules

- [[files/src_root_cause_analyzer_py]] — Root Cause Analyzer Orchestrator (`RootCauseAnalyzer`).
- [[files/src_root_cause_attribution_py]] — Dimension attribution calculator (`AttributionCalculator`).
- [[files/src_root_cause_correlator_py]] — Feature correlation engine (`FeatureCorrelator`).
- [[files/src_root_cause_segmenter_py]] — Data segmenter (`DataSegmenter`).
- [[files/src_root_cause_models_py]] — Root Cause Data Models (`RootCauseResult`).

---

## ⚡ Subsystem Connections
- Connected Anomaly Engine: [[03_Statistical_Anomaly_Hub]]
"""
    with open(VAULT_DIR / "04_Root_Cause_Engine_Hub.md", "w", encoding="utf-8") as f:
        f.write(rc_content)

    backend_content = """---
tags:
  - #hub
  - #backend
---
# 💙 05 FastAPI Backend Subsystem Hub

> **Master Hub**: [[00_Master_Hub]] | **Architecture**: [[01_System_Architecture]]

---

## 🔌 API Routers & Services

- [[files/backend_main_py]] — FastAPI Server Entry point.
- [[files/backend_routers_anomalies_py]] — Anomaly Detection REST Endpoint.
- [[files/backend_routers_rag_py]] — RAG Document Upload & Query REST Endpoint.
- [[files/backend_routers_datasets_py]] — Dataset Ingestion & Management Endpoint.
- [[files/backend_routers_health_py]] — Health Check Endpoint.

## 💾 Storage & Data Layer
- [[files/backend_storage_database_py]] — SQLite Database Connection & Session Pool.
- [[files/backend_storage_file_store_py]] — Local File Upload Manager.
- [[files/backend_dependencies_py]] — FastAPI Dependency Injection.
- [[files/backend_config_py]] — Application Settings & API Keys.
"""
    with open(VAULT_DIR / "05_FastAPI_Backend_Hub.md", "w", encoding="utf-8") as f:
        f.write(backend_content)

    frontend_content = """---
tags:
  - #hub
  - #frontend
---
# ❤️ 06 Frontend Application Subsystem Hub

> **Master Hub**: [[00_Master_Hub]] | **Architecture**: [[01_System_Architecture]]

---

## 🖥️ Dashboard Views & API Hooks

- [[files/frontend_src_routes_app_anomalies_tsx]] — Anomaly Detection Console View.
- [[files/frontend_src_routes_app_query_tsx]] — Clinical RAG Search Assistant View.
- [[files/frontend_src_routes_app_upload_tsx]] — Dataset & Document Upload Console View.
- [[files/frontend_src_routes_app_dashboard_tsx]] — Main Vital Metrics Dashboard.
- [[files/frontend_src_services_api_ts]] — Frontend REST API Client Service.
- [[files/frontend_src_types_backend-types_ts]] — TypeScript Types matching Backend Models.
"""
    with open(VAULT_DIR / "06_Frontend_App_Hub.md", "w", encoding="utf-8") as f:
        f.write(frontend_content)

def extract_python_imports(filepath):
    links = set()
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        for line in lines:
            line = line.strip()
            match = re.search(r'(?:from|import)\s+([\.\w]+)', line)
            if match:
                imp = match.group(1)
                if imp.startswith("."):
                    module_name = imp.lstrip(".")
                    if module_name:
                        target = filepath.parent / f"{module_name}.py"
                        if target.exists():
                            rel_t = target.relative_to(BASE_DIR)
                            links.add(clean_note_id(rel_t))
                elif "src." in imp or "backend." in imp:
                    parts = imp.split(".")
                    potential_path = BASE_DIR / ("/".join(parts) + ".py")
                    if potential_path.exists():
                        rel_t = potential_path.relative_to(BASE_DIR)
                        links.add(clean_note_id(rel_t))
                    else:
                        potential_dir_path = BASE_DIR / ("/".join(parts[:-1]) + ".py")
                        if potential_dir_path.exists():
                            rel_t = potential_dir_path.relative_to(BASE_DIR)
                            links.add(clean_note_id(rel_t))
    except Exception:
        pass
    return links

def parse_and_create_file_notes():
    target_dirs = [
        BASE_DIR / "src",
        BASE_DIR / "backend",
        BASE_DIR / "frontend" / "src" / "routes",
        BASE_DIR / "frontend" / "src" / "services",
        BASE_DIR / "frontend" / "src" / "types"
    ]
    
    processed_count = 0
    
    for tdir in target_dirs:
        if not tdir.exists():
            continue
            
        for root, dirs, files in os.walk(tdir):
            dirs[:] = [d for d in dirs if d not in ["__pycache__", "node_modules", ".git", "ui", "components"]]
            
            for file in files:
                if file.endswith((".py", ".ts", ".tsx")) and not file.startswith("__init__") and not file.endswith(".test.py"):
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(BASE_DIR)
                    
                    clean_id = clean_note_id(rel_path)
                    note_path = FILES_DIR / f"{clean_id}.md"
                    
                    tags = ["#code"]
                    hub_link = "[[00_Master_Hub]]"
                    
                    spath = str(rel_path).lower().replace("\\", "/")
                    if "src/rag" in spath:
                        tags.append("#rag")
                        hub_link = "[[02_RAG_Pipeline_Hub]]"
                    elif "src/detection" in spath:
                        tags.append("#anomaly")
                        hub_link = "[[03_Statistical_Anomaly_Hub]]"
                    elif "src/root_cause" in spath:
                        tags.append("#rootcause")
                        hub_link = "[[04_Root_Cause_Engine_Hub]]"
                    elif "backend" in spath:
                        tags.append("#backend")
                        hub_link = "[[05_FastAPI_Backend_Hub]]"
                    elif "frontend" in spath:
                        tags.append("#frontend")
                        hub_link = "[[06_Frontend_App_Hub]]"
                        
                    imported_notes = extract_python_imports(full_path)
                    
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as sf:
                            lines = sf.readlines()
                    except Exception:
                        lines = []
                        
                    classes = [l.strip().split("(")[0] for l in lines if l.strip().startswith(("class ", "export class ", "export interface "))]
                    functions = [l.strip().split("(")[0] for l in lines if l.strip().startswith(("def ", "async def ", "export function "))]
                    
                    content = f"""---
tags:
{chr(10).join([f"  - {t}" for t in tags])}
---
# 📄 `{file}`

> **File Path**: `{rel_path}`
> **Parent Hub**: {hub_link} | **Master Hub**: [[00_Master_Hub]]

---

## 🔗 Connected Dependencies & Imported Modules
"""
                    content += f"- Main Subsystem Hub: {hub_link}\n"
                    if imported_notes:
                        for imp_id in sorted(imported_notes):
                            content += f"- Imported Module: [[files/{imp_id}]]\n"
                    else:
                        content += "- *Standalone / Top-level Module*\n"
                        
                    content += f"""
---

## ⚙️ Key Symbols & Interfaces
"""
                    if classes:
                        for c in classes[:8]:
                            content += f"- `{c}`\n"
                    if functions:
                        for fn in functions[:10]:
                            content += f"- `{fn}`\n"
                    if not classes and not functions:
                        content += "*Core logic module*\n"
                        
                    content += f"""
---

## 💬 Token-Saving AI Summary
```text
Module: {rel_path} ({len(lines)} lines)
Tags: {', '.join(tags)}
Hub: {hub_link.replace('[[', '').replace(']]', '')}
Exports: {', '.join((classes + functions)[:5]) if (classes or functions) else 'System Execution'}
```
"""
                    with open(note_path, "w", encoding="utf-8") as f:
                        f.write(note_content if 'note_content' in locals() else content)
                        
                    processed_count += 1

    print(f"[+] Successfully created {processed_count} tightly connected module notes!")

def main():
    print("[*] Rebuilding Clean, Interconnected Obsidian Vault for InsightRAG AI...")
    reset_vault()
    write_obsidian_graph_config()
    build_core_hub_notes()
    parse_and_create_file_notes()
    print("[+] Vault successfully rebuilt! Open obsidian_vault in Obsidian now.")

if __name__ == "__main__":
    main()
