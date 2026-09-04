---
tags:
  - #code
  - #rag
---
# 📄 `ingestion.py`

> **File Path**: `src\rag\ingestion.py`
> **Parent Hub**: [[02_RAG_Pipeline_Hub]] | **Master Hub**: [[00_Master_Hub]]

---

## 🔗 Connected Dependencies & Imported Modules
- Main Subsystem Hub: [[02_RAG_Pipeline_Hub]]
- Imported Module: [[files/src_rag_models_py]]

---

## ⚙️ Key Symbols & Interfaces
- `class IngestionConfig:`
- `class DocumentIngester:`
- `def __post_init__`
- `def __init__`
- `def _init_extractors`
- `def ingest_file`
- `def ingest_directory`
- `def _detect_document_type`
- `def _extract_pdf`
- `def _extract_txt`
- `def _extract_markdown`
- `def _extract_csv`

---

## 💬 Token-Saving AI Summary
```text
Module: src\rag\ingestion.py (463 lines)
Tags: #code, #rag
Hub: 02_RAG_Pipeline_Hub
Exports: class IngestionConfig:, class DocumentIngester:, def __post_init__, def __init__, def _init_extractors
```
