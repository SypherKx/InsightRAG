---
tags:
  - #code
  - #rag
---
# 📄 `retriever.py`

> **File Path**: `src\rag\retriever.py`
> **Parent Hub**: [[02_RAG_Pipeline_Hub]] | **Master Hub**: [[00_Master_Hub]]

---

## 🔗 Connected Dependencies & Imported Modules
- Main Subsystem Hub: [[02_RAG_Pipeline_Hub]]
- Imported Module: [[files/src_rag_embeddings_py]]
- Imported Module: [[files/src_rag_models_py]]
- Imported Module: [[files/src_rag_vectorstore_py]]

---

## ⚙️ Key Symbols & Interfaces
- `class RAGRetriever:`
- `def __init__`
- `def retrieve`
- `def _lexical_search`
- `def _reciprocal_rank_fusion`
- `def _rerank_candidates`
- `def _build_filter`
- `def filter_func`
- `def _format_results`
- `def retrieve_with_context`
- `def search_similar_to_chunk`

---

## 💬 Token-Saving AI Summary
```text
Module: src\rag\retriever.py (449 lines)
Tags: #code, #rag
Hub: 02_RAG_Pipeline_Hub
Exports: class RAGRetriever:, def __init__, def retrieve, def _lexical_search, def _reciprocal_rank_fusion
```
