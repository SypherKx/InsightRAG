---
tags:
  - #code
---
# 📄 `pipeline.py`

> **File Path**: `src\ingestion\pipeline.py`
> **Parent Hub**: [[00_Master_Hub]] | **Master Hub**: [[00_Master_Hub]]

---

## 🔗 Connected Dependencies & Imported Modules
- Main Subsystem Hub: [[00_Master_Hub]]
- Imported Module: [[files/src_ingestion_cleaner_py]]
- Imported Module: [[files/src_ingestion_models_py]]
- Imported Module: [[files/src_ingestion_parser_py]]
- Imported Module: [[files/src_ingestion_storage_py]]
- Imported Module: [[files/src_ingestion_validator_py]]

---

## ⚙️ Key Symbols & Interfaces
- `class PipelineResult:`
- `class IngestionPipeline:`
- `def __post_init__`
- `def __init__`
- `def _validate_file`
- `def _compute_file_hash`
- `def _publish_event`
- `def _infer_time_column`
- `def _identify_dimensions`
- `def process_upload`
- `def _handle_failure`
- `def get_dataset_status`

---

## 💬 Token-Saving AI Summary
```text
Module: src\ingestion\pipeline.py (637 lines)
Tags: #code
Hub: 00_Master_Hub
Exports: class PipelineResult:, class IngestionPipeline:, def __post_init__, def __init__, def _validate_file
```
