---
tags:
  - #code
  - #rag
---
# 📄 `query_processor.py`

> **File Path**: `src\rag\query_processor.py`
> **Parent Hub**: [[02_RAG_Pipeline_Hub]] | **Master Hub**: [[00_Master_Hub]]

---

## 🔗 Connected Dependencies & Imported Modules
- Main Subsystem Hub: [[02_RAG_Pipeline_Hub]]
- *Standalone / Top-level Module*

---

## ⚙️ Key Symbols & Interfaces
- `class QueryProcessor:`
- `def intercept_greeting`
- `def extract_target_page`
- `def classify_intent`
- `def normalize_hinglish_query`
- `def decompose_query`
- `def expand_query_intent`
- `def _get_installed_ollama_models`
- `def generate_hyde_expansion`
- `def rewrite_query_with_llm`
- `def rewrite_conversational_query`

---

## 💬 Token-Saving AI Summary
```text
Module: src\rag\query_processor.py (557 lines)
Tags: #code, #rag
Hub: 02_RAG_Pipeline_Hub
Exports: class QueryProcessor:, def intercept_greeting, def extract_target_page, def classify_intent, def normalize_hinglish_query
```
