"""
CSV Parser with intelligent schema inference.

Handles parsing of CSV files with configurable options,
automatic type detection, and time series identification.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional

import pandas as pd
import numpy as np

from .models import ColumnSchema, ColumnType

logger = logging.getLogger(__name__)

# Sample size for schema inference (avoid loading full large file)
INFERENCE_SAMPLE_SIZE = 10000


class CSVParser:
    """
    CSV parser with automatic type inference and validation.

    Features:
    - Chunked reading for large files
    - Automatic type detection (int, float, datetime, categorical, text)
    - Time column identification
    - Encoding detection with fallback
    - Robust error handling
    """

    def __init__(
        self,
        delimiter: str = ",",
        quotechar: str = '"',
        escapechar: Optional[str] = None,
        encoding: str = "utf-8",
        chunk_size: int = 10000
    ):
        """
        Initialize CSV parser.

        Args:
            delimiter: Field delimiter
            quotechar: Quote character
            escapechar: Escape character
            encoding: File encoding
            chunk_size: Number of rows to read per chunk
        """
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.escapechar = escapechar
        self.encoding = encoding
        self.chunk_size = chunk_size

        # Statistics
        self.stats = {
            "rows_read": 0,
            "parse_errors": 0,
            "encoding_fallbacks": 0
        }

    def _detect_encoding(self, file_path: str | Path, sample_size: int = 10000) -> str:
        """
        Attempt to detect file encoding.

        Args:
            file_path: Path to file
            sample_size: Number of bytes to sample

        Returns:
            Detected encoding or fallback to utf-8
        """
        try:
            import chardet

            with open(file_path, 'rb') as f:
                raw_data = f.read(sample_size)
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                confidence = result.get('confidence', 0)

                logger.info(f"Detected encoding: {encoding} (confidence: {confidence:.2%})")

                if confidence > 0.7 and encoding:
                    return encoding
                else:
                    logger.warning("Low confidence in encoding detection, using utf-8")
                    return "utf-8"
        except ImportError:
            logger.warning("chardet not installed, using utf-8")
            return "utf-8"
        except Exception as e:
            logger.warning(f"Encoding detection failed: {e}, using utf-8")
            return "utf-8"

    def _infer_column_type(
        self,
        series: pd.Series,
        sample_size: int = 1000,
        time_column_candidates: Optional[List[str]] = None
    ) -> Tuple[ColumnType, Dict[str, Any]]:
        """
        Infer data type for a pandas Series.

        Args:
            series: Pandas Series
            sample_size: Number of non-null values to sample
            time_column_candidates: List of column names that might be time columns

        Returns:
            Tuple of (inferred_type, metadata)
        """
        col_name = series.name or "unknown"
        non_null = series.dropna()

        if len(non_null) == 0:
            return ColumnType.UNKNOWN, {"reason": "all_null"}

        # Sample for analysis
        sample = non_null.head(sample_size)

        # Check if it's a time column candidate (by name)
        is_time_candidate = (
            time_column_candidates and col_name in time_column_candidates
        ) or any(keyword in col_name.lower() for keyword in [
            'date', 'time', 'timestamp', 'dt', 'day', 'month', 'year',
            'created', 'updated', 'start', 'end'
        ])

        # Try to parse as datetime
        if is_time_candidate or non_null.dtype == 'datetime64[ns]':
            try:
                # Try pandas datetime conversion
                parsed = pd.to_datetime(sample, errors='coerce')
                success_rate = parsed.notna().mean()

                if success_rate > 0.7:  # At least 70% parseable as datetime
                    return ColumnType.DATETIME, {
                        "success_rate": float(success_rate),
                        "format": "inferred"
                    }
            except Exception:
                pass

        # Check for boolean (before numeric check since bool is numeric in pandas)
        if non_null.dtype == 'bool':
            return ColumnType.BOOLEAN, {}

        # Check numeric type
        if pd.api.types.is_numeric_dtype(series):
            # Check if all values are integers (integers stay as INTEGER even with low cardinality)
            if pd.api.types.is_integer_dtype(series):
                unique_sample = sample.nunique()
                return ColumnType.INTEGER, {"unique_values": int(unique_sample)}
            else:
                # Float - low cardinality floats may be categorical
                unique_sample = sample.nunique()
                if unique_sample / len(sample) < 0.1 and unique_sample <= 5:  # Low cardinality
                    return ColumnType.CATEGORICAL, {
                        "unique_ratio": float(unique_sample / len(sample))
                    }
                return ColumnType.FLOAT, {"unique_values": int(unique_sample)}

        # Check for boolean
        if non_null.dtype == 'bool':
            return ColumnType.BOOLEAN, {}

        # Check for categorical (low cardinality string)
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
            unique_count = sample.nunique()
            unique_ratio = unique_count / len(sample) if len(sample) > 0 else 0

            if unique_count <= 10 or (unique_ratio < 0.1 and unique_count < 50):
                return ColumnType.CATEGORICAL, {
                    "unique_count": int(unique_count),
                    "unique_ratio": float(unique_ratio)
                }
            else:
                # Check average length for text classification
                avg_len = sample.str.len().mean() if hasattr(sample, 'str') else 0
                if avg_len > 50:
                    return ColumnType.TEXT, {"avg_length": float(avg_len)}
                return ColumnType.TEXT, {"unique_ratio": float(unique_ratio)}

        return ColumnType.UNKNOWN, {"original_dtype": str(series.dtype)}

    def infer_schema(
        self,
        file_path: str | Path,
        time_column_candidates: Optional[List[str]] = None,
        user_provided_types: Optional[Dict[str, ColumnType]] = None,
        sample_rows: int = INFERENCE_SAMPLE_SIZE
    ) -> List[ColumnSchema]:
        """
        Infer schema from CSV file.

        Args:
            file_path: Path to CSV file
            time_column_candidates: Potential time column names
            user_provided_types: User-specified type overrides
            sample_rows: Number of rows to sample for inference

        Returns:
            List of ColumnSchema objects
        """
        logger.info(f"Inferring schema from: {file_path}")

        # Detect encoding
        encoding = self._detect_encoding(file_path)

        try:
            # Read sample for schema inference
            df_sample = pd.read_csv(
                file_path,
                delimiter=self.delimiter,
                quotechar=self.quotechar,
                escapechar=self.escapechar,
                encoding=encoding,
                nrows=sample_rows,
                low_memory=False
            )
        except UnicodeDecodeError:
            # Try with latin-1 fallback
            logger.warning(f"UTF-8 decode failed, trying latin-1")
            self.stats["encoding_fallbacks"] += 1
            encoding = "latin-1"
            df_sample = pd.read_csv(
                file_path,
                delimiter=self.delimiter,
                quotechar=self.quotechar,
                escapechar=self.escapechar,
                encoding=encoding,
                nrows=sample_rows,
                low_memory=False
            )

        logger.info(f"Sampled {len(df_sample)} rows with {len(df_sample.columns)} columns")

        schemas = []
        for col_name in df_sample.columns:
            series = df_sample[col_name]

            # Check if user provided type override
            user_type = None
            if user_provided_types and col_name in user_provided_types:
                user_type = user_provided_types[col_name]

            # Infer type
            inferred_type, metadata = self._infer_column_type(
                series,
                time_column_candidates=time_column_candidates if user_type is None else None
            )

            # Create schema
            schema = ColumnSchema(
                name=col_name,
                inferred_type=inferred_type,
                user_provided_type=user_type,
                nullable_count=int(series.isna().sum()),
                unique_count=int(series.nunique()),
                sample_values=series.dropna().head(5).tolist(),
                is_time_column=bool(inferred_type == ColumnType.DATETIME or
                                    (time_column_candidates and col_name in time_column_candidates)),
                is_dimension=False  # Will be set later based on user input
            )
            schemas.append(schema)

        logger.info(f"Schema inference complete: {len(schemas)} columns")
        return schemas

    def read_csv(
        self,
        file_path: str | Path,
        column_schema: Optional[List[ColumnSchema]] = None,
        time_column: Optional[str] = None,
        chunks: bool = False,
        chunk_size: Optional[int] = None
    ) -> pd.DataFrame | pd.io.parsers.TextFileReader:
        """
        Read CSV file with proper type conversions.

        Args:
            file_path: Path to CSV file
            column_schema: Optional schema to guide parsing
            time_column: Column to use as datetime index
            chunks: Whether to read in chunks
            chunk_size: Size of chunks (if None, uses self.chunk_size)

        Returns:
            DataFrame or TextFileReader for chunked reading
        """
        # Build dtype mapping from schema
        dtype_map = {}
        parse_dates = []

        if column_schema:
            for col_schema in column_schema:
                eff_type = col_schema.effective_type

                if eff_type == ColumnType.INTEGER:
                    dtype_map[col_schema.name] = 'Int64'  # Nullable integer
                elif eff_type == ColumnType.FLOAT:
                    dtype_map[col_schema.name] = 'float64'
                elif eff_type == ColumnType.BOOLEAN:
                    dtype_map[col_schema.name] = 'boolean'
                elif eff_type == ColumnType.CATEGORICAL:
                    dtype_map[col_schema.name] = 'category'
                elif eff_type == ColumnType.DATETIME:
                    parse_dates.append(col_schema.name)
                # TEXT and UNKNOWN use default object dtype

        # Detect encoding
        encoding = self._detect_encoding(file_path)

        read_params = {
            'delimiter': self.delimiter,
            'quotechar': self.quotechar,
            'escapechar': self.escapechar,
            'encoding': encoding,
            'low_memory': False,
            'dtype': dtype_map if dtype_map else None,
        }

        if parse_dates:
            read_params['parse_dates'] = parse_dates

        if chunks:
            chunk_sz = chunk_size or self.chunk_size
            read_params['chunksize'] = chunk_sz
            logger.info(f"Reading CSV in chunks of {chunk_sz} rows")
            return pd.read_csv(file_path, **read_params)
        else:
            logger.info(f"Reading full CSV")
            df = pd.read_csv(file_path, **read_params)

            # Set time column as index if specified
            if time_column and time_column in df.columns:
                df = df.set_index(pd.DatetimeIndex(df[time_column]))
                logger.info(f"Set index to datetime column: {time_column}")

            return df

    def validate_csv_structure(
        self,
        file_path: str | Path
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Perform basic structural validation of CSV file.

        Args:
            file_path: Path to CSV file

        Returns:
            Tuple of (is_valid, errors, metadata)
        """
        errors = []
        metadata = {}

        try:
            # Try to read first few rows
            test_df = pd.read_csv(
                file_path,
                delimiter=self.delimiter,
                quotechar=self.quotechar,
                escapechar=self.escapechar,
                nrows=100,
                low_memory=False
            )

            metadata['row_count'] = len(test_df)
            metadata['column_count'] = len(test_df.columns)
            metadata['columns'] = list(test_df.columns)

            # Check for empty DataFrame
            if len(test_df) == 0:
                errors.append("CSV file contains no data rows")

            # Check for duplicate column names in raw CSV header
            # (pandas auto-renames duplicates like 'a' -> 'a.1')
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_header = f.readline().strip()
                raw_cols = raw_header.split(self.delimiter)
            if len(raw_cols) != len(set(raw_cols)):
                dupes = [c for c in raw_cols if raw_cols.count(c) > 1]
                errors.append(f"Duplicate column names found: {dupes}")

            # Check if all columns are empty
            empty_cols = [col for col in test_df.columns if test_df[col].isna().all()]
            if len(empty_cols) == len(test_df.columns):
                errors.append("All columns are empty")
            elif empty_cols:
                logger.warning(f"Empty columns detected: {empty_cols}")

            return len(errors) == 0, errors, metadata

        except pd.errors.EmptyDataError:
            errors.append("CSV file is empty")
            return False, errors, metadata
        except pd.errors.ParserError as e:
            errors.append(f"CSV parsing error: {e}")
            return False, errors, metadata
        except Exception as e:
            errors.append(f"File validation error: {e}")
            return False, errors, metadata

    def get_file_info(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Get basic file information.

        Args:
            file_path: Path to file

        Returns:
            Dictionary with file metadata
        """
        path = Path(file_path)

        return {
            "filename": path.name,
            "size_bytes": path.stat().st_size,
            "size_mb": path.stat().st_size / (1024 * 1024),
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime),
            "created_at": datetime.fromtimestamp(path.stat().st_ctime),
            "suffix": path.suffix.lower()
        }
