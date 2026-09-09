"""
Data cleaning and preprocessing module.

Provides functions for handling missing values, outliers,
data type conversions, and preprocessing transformations.
"""

import logging
from typing import Dict, List, Tuple, Optional, Any

import pandas as pd
import numpy as np
from scipy import stats

from .models import ColumnType, ColumnSchema, PreprocessingConfig

logger = logging.getLogger(__name__)


class DataCleaner:
    """
    Data cleaning and preprocessing operations.

    Handles:
    - Missing value imputation
    - Outlier detection and handling
    - Data type conversions
    - Normalization and scaling
    - Feature engineering
    - Duplicate removal
    """

    def __init__(self, config: Optional[PreprocessingConfig] = None):
        """
        Initialize data cleaner.

        Args:
            config: Preprocessing configuration
        """
        self.config = config or PreprocessingConfig()
        self.report = {
            "rows_before": 0,
            "rows_after": 0,
            "columns_removed": [],
            "columns_added": [],
            "missing_values_filled": 0,
            "outliers_handled": 0,
            "duplicates_removed": 0
        }

    def _detect_outliers_iqr(self, series: pd.Series) -> pd.Series:
        """
        Detect outliers using IQR method.

        Args:
            series: Numeric series

        Returns:
            Boolean mask where True indicates outlier
        """
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        return (series < lower_bound) | (series > upper_bound)

    def _detect_outliers_zscore(self, series: pd.Series, threshold: float = 3.0) -> pd.Series:
        """
        Detect outliers using Z-score method.

        Args:
            series: Numeric series
            threshold: Z-score threshold

        Returns:
            Boolean mask where True indicates outlier
        """
        if series.std() == 0:
            return pd.Series([False] * len(series), index=series.index)

        z_scores = np.abs(stats.zscore(series.fillna(series.median()), nan_policy='omit'))
        return z_scores > threshold

    def handle_missing_values(
        self,
        df: pd.DataFrame,
        column_schemas: List[ColumnSchema],
        fill_strategy: Optional[Dict[str, str]] = None
    ) -> pd.DataFrame:
        """
        Handle missing values according to configuration.

        Args:
            df: Input DataFrame
            column_schemas: Column schema information
            fill_strategy: Per-column fill strategy override

        Returns:
            DataFrame with missing values handled
        """
        df_clean = df.copy()
        total_filled = 0

        # Strategy mapping
        strategy_map = {
            'mean': lambda s: s.mean(),
            'median': lambda s: s.median(),
            'mode': lambda s: s.mode()[0] if not s.mode().empty else None,
            'zero': 0,
            'ffill': None,  # Special handling
            'bfill': None,  # Special handling
        }

        for col_schema in column_schemas:
            col_name = col_schema.name
            if col_name not in df_clean.columns:
                continue

            col_series = df_clean[col_name]
            missing_count = col_series.isna().sum()

            if missing_count == 0:
                continue

            # Determine strategy for this column
            strategy = None
            if fill_strategy and col_name in fill_strategy:
                strategy = fill_strategy[col_name]
            else:
                if col_schema.effective_type in [ColumnType.INTEGER, ColumnType.FLOAT]:
                    strategy = self.config.fill_missing_numeric or 'median'
                elif col_schema.effective_type == ColumnType.CATEGORICAL:
                    strategy = self.config.fill_missing_categorical or 'mode'
                else:
                    # For text/datetime, use forward fill if time series
                    if col_schema.is_time_column:
                        strategy = 'ffill'
                    else:
                        continue  # Leave as is

            # Apply fill strategy
            if strategy == 'ffill':
                df_clean[col_name] = col_series.ffill()
                filled = col_series.isna().sum() - df_clean[col_name].isna().sum()
            elif strategy == 'bfill':
                df_clean[col_name] = col_series.bfill()
                filled = col_series.isna().sum() - df_clean[col_name].isna().sum()
            elif strategy in strategy_map:
                fill_value = strategy_map[strategy]
                if callable(fill_value):
                    fill_value = fill_value(col_series)

                df_clean[col_name] = col_series.fillna(fill_value)
                filled = missing_count - df_clean[col_name].isna().sum()
            else:
                logger.warning(f"Unknown fill strategy '{strategy}' for column {col_name}")
                continue

            total_filled += int(filled)
            logger.debug(f"Filled {filled} missing values in {col_name} using {strategy}")

        self.report['missing_values_filled'] += total_filled
        logger.info(f"Total missing values filled: {total_filled}")

        return df_clean

    def remove_duplicates(
        self,
        df: pd.DataFrame,
        subset: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Remove duplicate rows.

        Args:
            df: Input DataFrame
            subset: Columns to consider for duplication

        Returns:
            DataFrame with duplicates removed
        """
        rows_before = len(df)

        if subset:
            df_clean = df.drop_duplicates(subset=subset, keep='first')
        else:
            df_clean = df.drop_duplicates(keep='first')

        duplicates_removed = rows_before - len(df_clean)
        self.report['duplicates_removed'] += duplicates_removed

        logger.info(f"Removed {duplicates_removed} duplicate rows")
        return df_clean

    def handle_outliers(
        self,
        df: pd.DataFrame,
        column_schemas: List[ColumnSchema],
        method: str = 'iqr',
        treatment: str = 'cap'
    ) -> pd.DataFrame:
        """
        Detect and handle outliers in numeric columns.

        Args:
            df: Input DataFrame
            column_schemas: Column schema information
            method: Outlier detection method ('iqr' or 'zscore')
            treatment: Outlier treatment ('cap', 'remove', 'median')

        Returns:
            DataFrame with outliers handled
        """
        df_clean = df.copy()
        total_handled = 0

        for col_schema in column_schemas:
            col_name = col_schema.name
            if col_name not in df_clean.columns:
                continue

            if col_schema.effective_type not in [ColumnType.INTEGER, ColumnType.FLOAT]:
                continue

            col_series = df_clean[col_name].dropna()
            if len(col_series) == 0:
                continue

            # Detect outliers
            if method == 'iqr':
                outlier_mask = self._detect_outliers_iqr(col_series)
            elif method == 'zscore':
                outlier_mask = self._detect_outliers_zscore(col_series)
            else:
                logger.warning(f"Unknown outlier detection method: {method}")
                continue

            outlier_count = outlier_mask.sum()

            if outlier_count == 0:
                continue

            logger.info(f"Found {outlier_count} outliers in column '{col_name}'")

            # Apply treatment
            if treatment == 'cap':
                # Cap to bounds
                Q1 = col_series.quantile(0.25)
                Q3 = col_series.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR

                df_clean.loc[col_name] = df_clean[col_name].clip(lower=lower_bound, upper=upper_bound)

            elif treatment == 'remove':
                # Remove rows with outliers
                outlier_indices = df_clean.index[outlier_mask]
                df_clean = df_clean.drop(outlier_indices)

            elif treatment == 'median':
                # Replace with median
                median_val = col_series.median()
                df_clean.loc[outlier_mask, col_name] = median_val

            total_handled += int(outlier_count)

        self.report['outliers_handled'] += total_handled
        logger.info(f"Total outliers handled: {total_handled}")

        return df_clean

    def remove_constant_columns(
        self,
        df: pd.DataFrame,
        column_schemas: List[ColumnSchema]
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Remove columns with constant values (single unique value).

        Args:
            df: Input DataFrame
            column_schemas: Column schema information

        Returns:
            Tuple of (cleaned DataFrame, list of removed columns)
        """
        df_clean = df.copy()
        removed = []

        for col_schema in column_schemas:
            col_name = col_schema.name
            if col_name not in df_clean.columns:
                continue

            unique_count = df_clean[col_name].nunique(dropna=True)

            if unique_count <= 1:
                logger.info(f"Removing constant column: {col_name} (unique count: {unique_count})")
                df_clean = df_clean.drop(columns=[col_name])
                removed.append(col_name)

        self.report['columns_removed'].extend(removed)
        logger.info(f"Removed {len(removed)} constant columns")

        return df_clean, removed

    def remove_high_null_columns(
        self,
        df: pd.DataFrame,
        column_schemas: List[ColumnSchema],
        threshold: float = 0.8
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Remove columns with high percentage of null values.

        Args:
            df: Input DataFrame
            column_schemas: Column schema information
            threshold: Null percentage threshold (0.0 - 1.0)

        Returns:
            Tuple of (cleaned DataFrame, list of removed columns)
        """
        df_clean = df.copy()
        removed = []

        for col_schema in column_schemas:
            col_name = col_schema.name
            if col_name not in df_clean.columns:
                continue

            null_pct = df_clean[col_name].isna().mean()

            if null_pct >= threshold:
                logger.info(f"Removing high-null column: {col_name} (null %: {null_pct:.2%})")
                df_clean = df_clean.drop(columns=[col_name])
                removed.append(col_name)

        self.report['columns_removed'].extend(removed)
        logger.info(f"Removed {len(removed)} high-null columns")

        return df_clean, removed

    def normalize_numeric(
        self,
        df: pd.DataFrame,
        column_schemas: List[ColumnSchema],
        method: str = 'standard'
    ) -> Tuple[pd.DataFrame, Dict[str, Dict[str, float]]]:
        """
        Normalize numeric columns.

        Args:
            df: Input DataFrame
            column_schemas: Column schema information
            method: Normalization method ('standard', 'minmax', 'robust')

        Returns:
            Tuple of (normalized DataFrame, scaling params)
        """
        df_norm = df.copy()
        scaling_params = {}

        for col_schema in column_schemas:
            col_name = col_schema.name
            if col_name not in df_norm.columns:
                continue

            if col_schema.effective_type not in [ColumnType.INTEGER, ColumnType.FLOAT]:
                continue

            col_data = df_norm[col_name].dropna()
            if len(col_data) == 0:
                continue

            if method == 'standard':
                # Z-score normalization
                mean = col_data.mean()
                std = col_data.std()
                if std > 0:
                    df_norm[f"{col_name}_normalized"] = (df_norm[col_name] - mean) / std
                    scaling_params[col_name] = {'mean': float(mean), 'std': float(std)}
                else:
                    logger.warning(f"Column {col_name} has zero variance, skipping normalization")

            elif method == 'minmax':
                # Min-max scaling to [0, 1]
                min_val = col_data.min()
                max_val = col_data.max()
                range_val = max_val - min_val
                if range_val > 0:
                    df_norm[f"{col_name}_normalized"] = (df_norm[col_name] - min_val) / range_val
                    scaling_params[col_name] = {'min': float(min_val), 'max': float(max_val)}
                else:
                    logger.warning(f"Column {col_name} has no range, skipping normalization")

            elif method == 'robust':
                # Robust scaling using median and IQR
                median = col_data.median()
                Q1 = col_data.quantile(0.25)
                Q3 = col_data.quantile(0.75)
                iqr = Q3 - Q1
                if iqr > 0:
                    df_norm[f"{col_name}_normalized"] = (df_norm[col_name] - median) / iqr
                    scaling_params[col_name] = {'median': float(median), 'iqr': float(iqr)}
                else:
                    logger.warning(f"Column {col_name} has zero IQR, skipping normalization")

        if scaling_params:
            logger.info(f"Normalized {len(scaling_params)} numeric columns using {method} method")

        return df_norm, scaling_params

    def create_time_features(
        self,
        df: pd.DataFrame,
        time_column: str,
        features: List[str] = None
    ) -> pd.DataFrame:
        """
        Extract time-based features from datetime column.

        Args:
            df: Input DataFrame
            time_column: Time column name
            features: List of features to extract

        Returns:
            DataFrame with additional time features
        """
        if time_column not in df.columns:
            logger.warning(f"Time column '{time_column}' not found in DataFrame")
            return df

        df_features = df.copy()

        # Ensure datetime type
        if not pd.api.types.is_datetime64_any_dtype(df[time_column]):
            try:
                df_features[time_column] = pd.to_datetime(df_features[time_column])
            except Exception as e:
                logger.error(f"Failed to convert {time_column} to datetime: {e}")
                return df

        dt_series = df_features[time_column]
        features_to_create = features or self.config.time_features

        for feature in features_to_create:
            if feature == 'year':
                df_features[f"{time_column}_year"] = dt_series.dt.year
            elif feature == 'month':
                df_features[f"{time_column}_month"] = dt_series.dt.month
            elif feature == 'day':
                df_features[f"{time_column}_day"] = dt_series.dt.day
            elif feature == 'hour':
                df_features[f"{time_column}_hour"] = dt_series.dt.hour
            elif feature == 'minute':
                df_features[f"{time_column}_minute"] = dt_series.dt.minute
            elif feature == 'second':
                df_features[f"{time_column}_second"] = dt_series.dt.second
            elif feature == 'dayofweek':
                df_features[f"{time_column}_dayofweek"] = dt_series.dt.dayofweek
            elif feature == 'dayofyear':
                df_features[f"{time_column}_dayofyear"] = dt_series.dt.dayofyear
            elif feature == 'weekofyear':
                df_features[f"{time_column}_weekofyear"] = dt_series.dt.isocalendar().week
            elif feature == 'quarter':
                df_features[f"{time_column}_quarter"] = dt_series.dt.quarter
            elif feature == 'is_weekend':
                df_features[f"{time_column}_is_weekend"] = dt_series.dt.dayofweek.isin([5, 6])
            else:
                logger.warning(f"Unknown time feature: {feature}")

        self.report['columns_added'].extend([col for col in df_features.columns if col not in df.columns])
        logger.info(f"Created {len(self.report['columns_added'])} time features")

        return df_features

    def encode_categorical(
        self,
        df: pd.DataFrame,
        column_schemas: List[ColumnSchema],
        method: str = 'label'
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Encode categorical variables.

        Args:
            df: Input DataFrame
            column_schemas: Column schema information
            method: Encoding method ('label', 'onehot', 'ordinal')

        Returns:
            Tuple of (encoded DataFrame, encoding maps)
        """
        df_encoded = df.copy()
        encoding_maps = {}

        cat_cols = [
            cs.name for cs in column_schemas
            if cs.effective_type == ColumnType.CATEGORICAL and cs.name in df.columns
        ]

        for col_name in cat_cols:
            # Drop existing categories with too few samples (optional)
            value_counts = df[col_name].value_counts()
            min_samples = max(1, len(df) * 0.001)  # Min 0.1% of total

            rare_categories = value_counts[value_counts < min_samples].index
            if len(rare_categories) > 0:
                df_encoded[col_name] = df_encoded[col_name].replace(rare_categories, '_OTHER_')
                logger.debug(f"Grouped {len(rare_categories)} rare categories in {col_name}")

            if method == 'label':
                # Label encoding
                categories = df_encoded[col_name].astype('category').cat.categories.tolist()
                encoding_map = {cat: idx for idx, cat in enumerate(categories)}
                df_encoded[f"{col_name}_encoded"] = df_encoded[col_name].map(encoding_map)
                encoding_maps[col_name] = {
                    'method': 'label',
                    'mapping': encoding_map,
                    'categories': categories
                }

            elif method == 'onehot':
                # One-hot encoding
                dummies = pd.get_dummies(df_encoded[col_name], prefix=col_name, dummy_na=False)
                df_encoded = pd.concat([df_encoded, dummies], axis=1)
                encoding_maps[col_name] = {
                    'method': 'onehot',
                    'columns': dummies.columns.tolist()
                }

            elif method == 'ordinal':
                # Use existing order if determined by business logic, else alphabetical
                categories = sorted(df_encoded[col_name].dropna().unique().tolist())
                encoding_map = {cat: idx for idx, cat in enumerate(categories)}
                df_encoded[f"{col_name}_ordinal"] = df_encoded[col_name].map(encoding_map)
                encoding_maps[col_name] = {
                    'method': 'ordinal',
                    'mapping': encoding_map,
                    'categories': categories
                }

        logger.info(f"Encoded {len(cat_cols)} categorical columns using {method} method")
        return df_encoded, encoding_maps

    def clean_dataset(
        self,
        df: pd.DataFrame,
        column_schemas: List[ColumnSchema],
        time_column: Optional[str] = None,
        config: Optional[PreprocessingConfig] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Apply full cleaning pipeline.

        Args:
            df: Input DataFrame
            column_schemas: Column schema information
            time_column: Time column for indexing
            config: Preprocessing configuration

        Returns:
            Tuple of (cleaned DataFrame, cleaning report)
        """
        if config:
            self.config = config

        self.report = {
            "rows_before": len(df),
            "rows_after": len(df),
            "columns_original": list(df.columns),
            "columns_removed": [],
            "columns_added": [],
            "missing_values_filled": 0,
            "outliers_handled": 0,
            "duplicates_removed": 0
        }

        df_clean = df.copy()
        original_columns = set(df_clean.columns)

        logger.info("Starting cleaning pipeline")

        # 1. Remove duplicates
        if self.config.drop_duplicate_rows:
            df_clean = self.remove_duplicates(df_clean)

        # 2. Remove constant columns
        if self.config.drop_constant_columns:
            df_clean, const_removed = self.remove_constant_columns(df_clean, column_schemas)

        # 3. Remove high null columns
        if self.config.drop_high_null_columns:
            df_clean, null_removed = self.remove_high_null_columns(df_clean, column_schemas, threshold=0.8)

        # 4. Handle missing values
        if self.config.fill_missing_numeric or self.config.fill_missing_categorical:
            df_clean = self.handle_missing_values(df_clean, column_schemas)

        # 5. Handle outliers
        if False:  # Future: add config option for outlier handling
            df_clean = self.handle_outliers(df_clean, column_schemas)

        # 6. Create time features
        if self.config.create_time_features and time_column:
            df_clean = self.create_time_features(df_clean, time_column)

        # 7. Encode categorical variables
        if self.config.encode_categorical:
            df_clean, enc_maps = self.encode_categorical(df_clean, column_schemas, self.config.categorical_encoding)

        # 8. Normalize numeric columns
        if self.config.normalize_numeric:
            df_clean, scaler_params = self.normalize_numeric(
                df_clean,
                column_schemas,
                self.config.normalization_method
            )
            self.report['scaler_params'] = scaler_params

        self.report['rows_after'] = len(df_clean)
        self.report['columns_final'] = list(df_clean.columns)
        self.report['new_columns'] = [col for col in df_clean.columns if col not in original_columns]

        logger.info(f"Cleaning complete: {len(df)} -> {len(df_clean)} rows")

        return df_clean, self.report


def clean_data(
    df: pd.DataFrame,
    column_schemas: List[ColumnSchema],
    time_column: Optional[str] = None,
    config: Optional[PreprocessingConfig] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Convenience function for data cleaning.

    Args:
        df: Input DataFrame
        column_schemas: Column schema information
        time_column: Time column for indexing
        config: Preprocessing configuration

    Returns:
        Tuple of (cleaned DataFrame, cleaning report)
    """
    cleaner = DataCleaner(config)
    return cleaner.clean_dataset(df, column_schemas, time_column, config)
