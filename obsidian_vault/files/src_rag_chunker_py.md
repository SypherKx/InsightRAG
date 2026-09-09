---
tags:
  - #code
  - #rag
---
# 📄 `chunker.py`

> **File Path**: `src\rag\chunker.py`
> **Parent Hub**: [[02_RAG_Pipeline_Hub]] | **Master Hub**: [[00_Master_Hub]]

---

## 🔗 Connected Dependencies & Imported Modules
- Main Subsystem Hub: [[02_RAG_Pipeline_Hub]]
- *Standalone / Top-level Module*

---

## ⚙️ Key Symbols & Interfaces
- `class ChunkConfig:`
- `class TextChunker:`
- `def build_contextual_chunk`
- `def is_section_heading`
- `def is_markdown_table`
- `def split_markdown_table_by_rows`
- `def __init__`
- `def _compile_separator_pattern`
- `def _count_tokens`
- `def _split_by_separators`
- `def chunk_text`
- `def _clean_text`

---

## 💬 Token-Saving AI Summary
```text
Module: src\rag\chunker.py (586 lines)
Tags: #code, #rag
Hub: 02_RAG_Pipeline_Hub
Exports: class ChunkConfig:, class TextChunker:, def build_contextual_chunk, def is_section_heading, def is_markdown_table
```
