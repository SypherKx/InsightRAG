"""
Data quality validation module.

Provides comprehensive validation rules and checks for
assessing dataset quality before processing.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

import pandas as pd
import numpy as np

from .models import (
    ColumnSchema,
    ColumnType,
    DataQualityMetrics,
    ValidationResult,
    ValidationReport,
    ValidationRule
)

logger = logging.getLogger(__name__)


class DataValidator:
    """
    Data quality validator with configurable rules.

    Validates:
    - Missing value thresholds
    - Duplicate detection
    - Type consistency
    - Value range validity
    - Pattern matching (regex)
    - Statistical anomalies
    """

    # Default validation thresholds
    DEFAULT_MAX_MISSING_PCT = 0.20  # 20% max missing
    DEFAULT_MAX_DUPLICATE_PCT = 0.10  # 10% max duplicates
    DEFAULT_MIN_UNIQUE_VALUES = 2  # At least 2 unique values for categorical
    DEFAULT_MAX_ZERO_VALUES = 0.20  # 20% max zeros for numeric
    DEFAULT_MIN_ROWS = 10  # Minimum rows required

    def __init__(
        self,
        custom_rules: Optional[List[ValidationRule]] = None,
        severity_thresholds: Optional[Dict[str, str]] = None
    ):
        """
        Initialize validator.

        Args:
            custom_rules: Custom validation rules
            severity_thresholds: Severity mapping for rule violations
        """
        self.custom_rules = custom_rules or []
        self.severity_thresholds = severity_thresholds or {
            'missing_values': 'high',
            'duplicates': 'medium',
            'constant_column': 'medium',
            'low_variance': 'low',
            'type_inconsistency': 'high',
            'out_of_range': 'medium',
            'pattern_mismatch': 'medium',
            'statistical_anomaly': 'high'
        }

        self.results = []

    def _calculate_quality_metrics(
        self,
        df: pd.DataFrame,
        column_schemas: List[ColumnSchema]
    ) -> DataQualityMetrics:
        """
        Calculate comprehensive data quality metrics.

        Args:
            df: Input DataFrame
            column_schemas: Column schema information

        Returns:
            DataQualityMetrics object
        """
        total_rows = len(df)
        total_columns = len(df.columns)

        # Missing values
        missing_total = df.isna().sum().sum() if total_rows > 0 else 0
        total_cells = total_rows * total_columns if total_rows > 0 else 1
        missing_pct = (missing_total / total_cells * 100) if total_cells > 0 else 0

        # Duplicate rows
        duplicate_count = df.duplicated().sum() if total_rows > 0 else 0
        duplicate_pct = (duplicate_count / total_rows * 100) if total_rows > 0 else 0

        # Columns with missing values
        cols_with_missing = df.columns[df.isna().any()].tolist()

        # High null threshold columns
        high_null_threshold = 0.5
        cols_high_null = df.columns[df.isna().mean() >= high_null_threshold].tolist()

        # Constant columns
        constant_cols = [
            col for col in df.columns
            if df[col].nunique(dropna=True) <= 1
        ]

        # Low variance columns (numeric with very small std)
        low_variance_cols = []
        for col_schema in column_schemas:
            if col_schema.name in df.columns and col_schema.effective_type in [ColumnType.INTEGER, ColumnType.FLOAT]:
                col_data = df[col_schema.name].dropna()
                if len(col_data) > 0:
                    try:
                        col_numeric = pd.to_numeric(col_data, errors='coerce').dropna()
                        if len(col_numeric) < 2:
                            continue
                        std = col_numeric.std()
                        mean = col_numeric.mean()
                        if pd.isna(std) or pd.isna(mean):
                            continue
                        std_f = float(std)
                        mean_f = float(mean)
                        if mean_f != 0 and (std_f / abs(mean_f) < 0.01):  # CV < 1%
                            low_variance_cols.append(col_schema.name)
                        elif mean_f == 0 and std_f < 0.01:
                            low_variance_cols.append(col_schema.name)
                    except Exception:
                        continue

        metrics = DataQualityMetrics(
            total_rows=total_rows,
            total_columns=total_columns,
            missing_values_total=int(missing_total),
            missing_values_percentage=missing_pct,
            duplicate_rows=int(duplicate_count),
            duplicate_rows_percentage=duplicate_pct,
            columns_with_missing=cols_with_missing,
            columns_high_null_threshold=cols_high_null,
            constant_columns=constant_cols,
            low_variance_columns=low_variance_cols
        )

        logger.info(f"Quality metrics: {metrics.model_dump() if hasattr(metrics, 'model_dump') else metrics.dict()}")

        return metrics

    def validate_missing_values(
        self,
        df: pd.DataFrame,
        rule: ValidationRule
    ) -> ValidationResult:
        """
        Validate missing value thresholds.

        Args:
            df: Input DataFrame
            rule: Validation rule configuration

        Returns:
            ValidationResult
        """
        threshold = rule.threshold or self.DEFAULT_MAX_MISSING_PCT

        total_cells = len(df) * len(df.columns)
        missing_total = df.isna().sum().sum()
        missing_pct = missing_total / total_cells if total_cells > 0 else 0

        passed = missing_pct <= threshold

        details = {
            "missing_count": int(missing_total),
            "total_cells": int(total_cells),
            "missing_percentage": round(missing_pct * 100, 2),
            "threshold_percentage": round(threshold * 100, 2)
        }

        if rule.column:
            # Column-specific check
            col_missing = df[rule.column].isna().sum()
            col_missing_pct = col_missing / len(df) if len(df) > 0 else 0
            passed = col_missing_pct <= threshold
            details.update({
                "column": rule.column,
                "column_missing_count": int(col_missing),
                "column_missing_percentage": round(col_missing_pct * 100, 2)
            })

        severity = rule.severity or self.severity_thresholds['missing_values']

        message = (
            f"Missing values {'within' if passed else 'exceed'} threshold: "
            f"{details['missing_percentage']}% <= {details['threshold_percentage']}%"
        )

        return ValidationResult(
            rule=rule,
            passed=passed,
            severity=severity,
            message=message,
            details=details
        )

    def validate_duplicates(
        self,
        df: pd.DataFrame,
        rule: ValidationRule
    ) -> ValidationResult:
        """
        Validate duplicate row thresholds.

        Args:
            df: Input DataFrame
            rule: Validation rule configuration

        Returns:
            ValidationResult
        """
        threshold = rule.threshold or self.DEFAULT_MAX_DUPLICATE_PCT

        duplicate_count = df.duplicated().sum()
        duplicate_pct = duplicate_count / len(df) if len(df) > 0 else 0

        passed = duplicate_pct <= threshold

        details = {
            "duplicate_count": int(duplicate_count),
            "total_rows": len(df),
            "duplicate_percentage": round(duplicate_pct * 100, 2),
            "threshold_percentage": round(threshold * 100, 2)
        }

        severity = rule.severity or self.severity_thresholds['duplicates']

        message = (
            f"Duplicate rows {'within' if passed else 'exceed'} threshold: "
            f"{details['duplicate_percentage']}% <= {details['threshold_percentage']}%"
        )

        return ValidationResult(
            rule=rule,
            passed=passed,
            severity=severity,
            message=message,
            details=details
        )

    def validate_constant_columns(
        self,
        df: pd.DataFrame,
        rule: ValidationRule
    ) -> ValidationResult:
        """
        Validate for constant columns (no variance).

        Args:
            df: Input DataFrame
            rule: Validation rule configuration

        Returns:
            ValidationResult
        """
        threshold = rule.threshold or 0  # No tolerance for constant columns

        constant_cols = []
        for col in df.columns:
            if df[col].nunique(dropna=True) <= 1:
                constant_cols.append(col)

        constant_count = len(constant_cols)
        passed = constant_count <= threshold

        details = {
            "constant_column_count": constant_count,
            "constant_columns": constant_cols,
            "threshold": threshold
        }

        severity = rule.severity or self.severity_thresholds['constant_column']

        message = (
            f"Constant columns: {constant_count} found "
            f"({'within' if passed else 'exceed'} threshold of {threshold})"
        )

        return ValidationResult(
            rule=rule,
            passed=passed,
            severity=severity,
            message=message,
            details=details
        )

    def validate_min_rows(
        self,
        df: pd.DataFrame,
        rule: ValidationRule
    ) -> ValidationResult:
        """
        Validate minimum row count.

        Args:
            df: Input DataFrame
            rule: Validation rule configuration

        Returns:
            ValidationResult
        """
        threshold = rule.threshold or self.DEFAULT_MIN_ROWS
        row_count = len(df)
        passed = row_count >= threshold

        details = {
            "row_count": row_count,
            "threshold": threshold
        }

        severity = rule.severity or 'medium'

        message = (
            f"Row count {'meets' if passed else 'below'} minimum: "
            f"{row_count} >= {threshold}"
        )

        return ValidationResult(
            rule=rule,
            passed=passed,
            severity=severity,
            message=message,
            details=details
        )

    def validate_type_consistency(
        self,
        df: pd.DataFrame,
        column_schemas: List[ColumnSchema],
        rule: ValidationRule
    ) -> ValidationResult:
        """
        Validate that column values are consistent with inferred types.

        Args:
            df: Input DataFrame
            column_schemas: Column schema information
            rule: Validation rule configuration

        Returns:
            ValidationResult
        """
        inconsistencies = []

        for col_schema in column_schemas:
            col_name = col_schema.name
            if col_name not in df.columns:
                continue

            col_type = col_schema.effective_type
            col_series = df[col_name]

            # Check for type inconsistencies
            try:
                if col_type == ColumnType.INTEGER:
                    non_numeric = col_series.dropna().apply(
                        lambda x: not isinstance(x, (int, np.integer)) and not str(x).isdigit()
                    )
                    if non_numeric.any():
                        inconsistencies.append(f"{col_name}: contains non-integer values")

                elif col_type == ColumnType.FLOAT:
                    col_data = col_series.dropna()
                    # If dtype is already object/string, there may be mixed types
                    if col_data.dtype == 'object':
                        non_numeric = pd.to_numeric(col_data, errors='coerce')
                        if non_numeric.isna().any():
                            inconsistencies.append(f"{col_name}: contains non-numeric values")
                    elif not pd.api.types.is_numeric_dtype(col_data):
                        inconsistencies.append(f"{col_name}: contains non-numeric values")

                elif col_type == ColumnType.BOOLEAN:
                    valid_values = {True, False, 'true', 'false', 'True', 'False', 1, 0}
                    invalid = set(col_series.dropna().unique()) - valid_values
                    if invalid:
                        inconsistencies.append(f"{col_name}: contains non-boolean values {invalid}")

            except Exception as e:
                logger.warning(f"Type check failed for {col_name}: {e}")
                inconsistencies.append(f"{col_name}: type check error ({e})")

        passed = len(inconsistencies) == 0
        severity = rule.severity or self.severity_thresholds['type_inconsistency']

        message = (
            f"Type consistency {'check passed' if passed else 'check failed'}"
            + (f": {', '.join(inconsistencies)}" if not passed else "")
        )

        return ValidationResult(
            rule=rule,
            passed=passed,
            severity=severity,
            message=message,
            details={"inconsistencies": inconsistencies}
        )

    def validate_dataset(
        self,
        df: pd.DataFrame,
        column_schemas: List[ColumnSchema],
        custom_rules: Optional[List[ValidationRule]] = None
    ) -> ValidationReport:
        """
        Run comprehensive validation on dataset.

        Args:
            df: Input DataFrame
            column_schemas: Column schema information
            custom_rules: Additional custom validation rules

        Returns:
            ValidationReport with all results
        """
        logger.info("Starting dataset validation")

        all_results = []
        warnings = []
        errors = []

        # Handle empty DataFrame early
        if len(df.columns) == 0 or len(df) == 0:
            empty_metrics = DataQualityMetrics(
                total_rows=len(df),
                total_columns=len(df.columns),
                missing_values_total=0,
                missing_values_percentage=0.0,
                duplicate_rows=0,
                duplicate_rows_percentage=0.0,
            )
            errors.append("DataFrame is empty or has no columns")
            return ValidationReport(
                dataset_id=None,
                overall_status="failed",
                quality_metrics=empty_metrics,
                validation_results=[],
                warnings=[],
                errors=errors,
                created_at=datetime.utcnow()
            )
        warnings = []
        errors = []

        # Calculate quality metrics first
        metrics = self._calculate_quality_metrics(df, column_schemas)

        # Built-in validations
        builtin_rules = [
            ValidationRule(
                rule_type="min_rows",
                parameters={"min_rows": self.DEFAULT_MIN_ROWS},
                threshold=self.DEFAULT_MIN_ROWS,
                severity="medium"
            ),
            ValidationRule(
                rule_type="missing_values",
                parameters={"max_percentage": self.DEFAULT_MAX_MISSING_PCT},
                threshold=self.DEFAULT_MAX_MISSING_PCT,
                severity="medium"
            ),
            ValidationRule(
                rule_type="duplicates",
                parameters={"max_percentage": self.DEFAULT_MAX_DUPLICATE_PCT},
                threshold=self.DEFAULT_MAX_DUPLICATE_PCT,
                severity="medium"
            ),
            ValidationRule(
                rule_type="constant_columns",
                parameters={"max_count": 0},
                threshold=0,
                severity="medium"
            ),
            ValidationRule(
                rule_type="type_consistency",
                parameters={},
                severity="high"
            )
        ]

        # Run built-in validations
        for rule in builtin_rules:
            try:
                if rule.rule_type == "missing_values":
                    result = self.validate_missing_values(df, rule)
                elif rule.rule_type == "duplicates":
                    result = self.validate_duplicates(df, rule)
                elif rule.rule_type == "constant_columns":
                    result = self.validate_constant_columns(df, rule)
                elif rule.rule_type == "min_rows":
                    result = self.validate_min_rows(df, rule)
                elif rule.rule_type == "type_consistency":
                    result = self.validate_type_consistency(df, column_schemas, rule)
                else:
                    continue

                all_results.append(result)

                if not result.passed and result.severity in ['high', 'critical']:
                    errors.append(result.message)
                elif not result.passed:
                    warnings.append(result.message)

            except Exception as e:
                logger.error(f"Validation rule {rule.rule_type} failed: {e}")
                errors.append(f"Validation error in {rule.rule_type}: {str(e)}")

        # Run custom rules
        all_custom_rules = custom_rules or self.custom_rules
        for rule in all_custom_rules:
            try:
                if rule.rule_type == "custom_range":
                    df_result = self._validate_range(df, rule)
                elif rule.rule_type == "custom_pattern":
                    df_result = self._validate_pattern(df, rule)
                elif rule.rule_type == "custom_expression":
                    df_result = self._validate_expression(df, rule)
                else:
                    logger.warning(f"Unknown custom rule type: {rule.rule_type}")
                    continue

                all_results.append(df_result)

                if not df_result.passed:
                    if df_result.severity in ['high', 'critical']:
                        errors.append(df_result.message)
                    else:
                        warnings.append(df_result.message)

            except Exception as e:
                logger.error(f"Custom validation rule {rule.rule_type} failed: {e}")
                errors.append(f"Validation error in {rule.rule_type}: {str(e)}")

        # Determine overall status
        if errors:
            overall_status = "failed"
        elif warnings:
            overall_status = "warning"
        else:
            overall_status = "passed"

        # Calculate quality score (0-1)
        passed_count = sum(1 for r in all_results if r.passed)
        total_count = len(all_results)
        quality_score = passed_count / total_count if total_count > 0 else 0.0

        report = ValidationReport(
            dataset_id=None,
            overall_status=overall_status,
            quality_metrics=metrics,
            validation_results=all_results,
            warnings=warnings,
            errors=errors,
            created_at=datetime.utcnow()
        )

        logger.info(
            f"Validation complete: {overall_status}, "
            f"score={quality_score:.2%}, errors={len(errors)}, warnings={len(warnings)}"
        )

        return report

    def _validate_range(
        self,
        df: pd.DataFrame,
        rule: ValidationRule
    ) -> ValidationResult:
        """
        Custom range validation for a column.

        Args:
            df: Input DataFrame
            rule: Validation rule with min/max parameters

        Returns:
            ValidationResult
        """
        column = rule.column
        if not column or column not in df.columns:
            return ValidationResult(
                rule=rule,
                passed=False,
                severity=rule.severity or 'high',
                message=f"Column '{column}' not found",
                details={}
            )

        min_val = rule.parameters.get('min')
        max_val = rule.parameters.get('max')

        col_series = df[column].dropna()
        out_of_range = pd.Series([False] * len(col_series), index=col_series.index)

        if min_val is not None:
            out_of_range |= (col_series < min_val)
        if max_val is not None:
            out_of_range |= (col_series > max_val)

        out_of_range_count = out_of_range.sum()
        out_of_range_pct = out_of_range_count / len(col_series) if len(col_series) > 0 else 0

        passed = out_of_range_pct <= (rule.threshold or 0)

        details = {
            "column": column,
            "out_of_range_count": int(out_of_range_count),
            "out_of_range_percentage": round(out_of_range_pct * 100, 2),
            "min_value": min_val,
            "max_value": max_val,
            "sample_out_of_range": col_series[out_of_range].head(5).tolist()
        }

        message = (
            f"Column '{column}' values {'within' if passed else 'out of'} range "
            f"[{min_val}, {max_val}]: {details['out_of_range_percentage']}% out of range"
        )

        return ValidationResult(
            rule=rule,
            passed=passed,
            severity=rule.severity or 'medium',
            message=message,
            details=details
        )

    def _validate_pattern(
        self,
        df: pd.DataFrame,
        rule: ValidationRule
    ) -> ValidationResult:
        """
        Custom regex pattern validation for a column.

        Args:
            df: Input DataFrame
            rule: Validation rule with pattern parameter

        Returns:
            ValidationResult
        """
        import re

        column = rule.column
        pattern = rule.parameters.get('pattern')
        if not pattern:
            return ValidationResult(
                rule=rule,
                passed=False,
                severity=rule.severity or 'high',
                message="No pattern provided",
                details={}
            )

        if column not in df.columns:
            return ValidationResult(
                rule=rule,
                passed=False,
                severity=rule.severity or 'high',
                message=f"Column '{column}' not found",
                details={}
            )

        regex = re.compile(pattern)
        col_series = df[column].astype(str).dropna()

        matches = col_series.str.match(regex, na=False)
        mismatch_count = (~matches).sum()
        mismatch_pct = mismatch_count / len(col_series) if len(col_series) > 0 else 0

        passed = mismatch_pct <= (rule.threshold or 0)

        details = {
            "column": column,
            "mismatch_count": int(mismatch_count),
            "mismatch_percentage": round(mismatch_pct * 100, 2),
            "pattern": pattern,
            "sample_mismatches": col_series[~matches].head(5).tolist()
        }

        message = (
            f"Column '{column}' values {'match' if passed else 'do not match'} "
            f"pattern: {details['mismatch_percentage']}% mismatch"
        )

        return ValidationResult(
            rule=rule,
            passed=passed,
            severity=rule.severity or 'medium',
            message=message,
            details=details
        )

    def _validate_expression(
        self,
        df: pd.DataFrame,
        rule: ValidationRule
    ) -> ValidationResult:
        """
        Custom expression validation (evaluates pandas expression).

        Args:
            df: Input DataFrame
            rule: Validation rule with expression parameter

        Returns:
            ValidationResult
        """
        expression = rule.parameters.get('expression')
        if not expression:
            return ValidationResult(
                rule=rule,
                passed=False,
                severity=rule.severity or 'high',
                message="No expression provided",
                details={}
            )

        try:
            # Evaluate expression on DataFrame
            result = df.eval(expression, engine='python')
            passed = result.all()

            details = {
                "expression": expression,
                "rows_evaluated": len(df),
                "rows_passing": int(result.sum()),
                "rows_failing": int((~result).sum())
            }

            severity = rule.severity or 'medium'
            message = (
                f"Expression validation {'passed' if passed else 'failed'}: {expression}"
            )

        except Exception as e:
            passed = False
            severity = rule.severity or 'high'
            message = f"Expression evaluation error: {str(e)}"
            details = {"error": str(e), "expression": expression}

        return ValidationResult(
            rule=rule,
            passed=passed,
            severity=severity,
            message=message,
            details=details
        )


def validate_dataset(
    df: pd.DataFrame,
    column_schemas: List[ColumnSchema],
    custom_rules: Optional[List[ValidationRule]] = None
) -> ValidationReport:
    """
    Convenience function for dataset validation.

    Args:
        df: Input DataFrame
        column_schemas: Column schema information
        custom_rules: Custom validation rules

    Returns:
        ValidationReport
    """
    validator = DataValidator(custom_rules=custom_rules)
    return validator.validate_dataset(df, column_schemas)


def create_default_validation_rules() -> List[ValidationRule]:
    """
    Create default validation rules for standard datasets.

    Returns:
        List of default ValidationRule objects
    """
    return [
        ValidationRule(
            rule_type="min_rows",
            column=None,
            parameters={"min_rows": 10},
            threshold=10,
            severity="medium"
        ),
        ValidationRule(
            rule_type="missing_values",
            column=None,
            parameters={"max_percentage": 0.20},
            threshold=0.20,
            severity="medium"
        ),
        ValidationRule(
            rule_type="duplicates",
            column=None,
            parameters={"max_percentage": 0.10},
            threshold=0.10,
            severity="medium"
        ),
        ValidationRule(
            rule_type="constant_columns",
            column=None,
            parameters={"max_count": 0},
            threshold=0,
            severity="medium"
        ),
        ValidationRule(
            rule_type="type_consistency",
            column=None,
            parameters={},
            severity="high"
        )
    ]
