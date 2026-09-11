---
tags:
  - #code
  - #backend
---
# 📄 `rag_service.py`

> **File Path**: `backend\services\rag_service.py`
> **Parent Hub**: [[05_FastAPI_Backend_Hub]] | **Master Hub**: [[00_Master_Hub]]

---

## 🔗 Connected Dependencies & Imported Modules
- Main Subsystem Hub: [[05_FastAPI_Backend_Hub]]
- Imported Module: [[files/backend_services_ollama_manager_py]]
- Imported Module: [[files/backend_services_rag_task_manager_py]]

---

## ⚙️ Key Symbols & Interfaces
- `class RAGService:`
- `def build_chatgpt_rag_prompt`
- `def __init__`
- `def set_hardware_mode`
- `def _safe_terminal_print`
- `def get_hardware_mode`
- `def is_available`
- `def ingest_documents`
- `def start_background_ingestion`
- `def _run_ingestion_worker`
- `def progress_hook`

---

## 💬 Token-Saving AI Summary
```text
Module: backend\services\rag_service.py (887 lines)
Tags: #code, #backend
Hub: 05_FastAPI_Backend_Hub
Exports: class RAGService:, def build_chatgpt_rag_prompt, def __init__, def set_hardware_mode, def _safe_terminal_print
```
