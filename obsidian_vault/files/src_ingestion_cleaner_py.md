---
tags:
  - #code
---
# 📄 `cleaner.py`

> **File Path**: `src\ingestion\cleaner.py`
> **Parent Hub**: [[00_Master_Hub]] | **Master Hub**: [[00_Master_Hub]]

---

## 🔗 Connected Dependencies & Imported Modules
- Main Subsystem Hub: [[00_Master_Hub]]
- Imported Module: [[files/src_ingestion_models_py]]

---

## ⚙️ Key Symbols & Interfaces
- `class DataCleaner:`
- `def __init__`
- `def _detect_outliers_iqr`
- `def _detect_outliers_zscore`
- `def handle_missing_values`
- `def remove_duplicates`
- `def handle_outliers`
- `def remove_constant_columns`
- `def remove_high_null_columns`
- `def normalize_numeric`
- `def create_time_features`

---

## 💬 Token-Saving AI Summary
```text
Module: src\ingestion\cleaner.py (655 lines)
Tags: #code
Hub: 00_Master_Hub
Exports: class DataCleaner:, def __init__, def _detect_outliers_iqr, def _detect_outliers_zscore, def handle_missing_values
```
