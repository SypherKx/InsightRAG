// ─── Dataset Types ───

export interface ColumnSchema {
  name: string;
  type: string;
  inferred: boolean;
}

export interface Dataset {
  id: string;
  name: string;
  status: string;
  row_count: number;
  column_count: number;
  columns: ColumnSchema[];
  time_column?: string;
  dimensions: string[];
  quality_score?: number;
  anomaly_count: number;
  uploaded_at?: string;
  processing_completed_at?: string;
  error_message?: string;
}

// ─── Anomaly Types ───

export interface Anomaly {
  id: string;
  dataset_id: string;
  timestamp?: string;
  metric: string;
  value: number;
  expected_min?: number;
  expected_max?: number;
  anomaly_type: string;
  severity: number;
  confidence: number;
  dimensions: Record<string, string>;
}

export interface AnomalySummary {
  total_anomalies: number;
  avg_severity: number;
  by_type: Record<string, number>;
  by_severity_level: Record<string, number>;
}

// ─── Root Cause Types ───

export interface Driver {
  segment: string;
  contribution: number;
  baseline_ratio: number;
  evidence?: string;
}

export interface Correlation {
  metric: string;
  coefficient: number;
  p_value?: number;
  lag_hours?: number;
}

export interface ChangePoint {
  detected_at?: string;
  confidence: number;
  before_mean: number;
  after_mean: number;
  change_magnitude: number;
}

export interface RootCause {
  primary_drivers: Driver[];
  correlations: Correlation[];
  change_point?: ChangePoint;
  hypothesis: string;
  confidence: number;
  methods_used: string[];
}

// ─── Explanation Types ───

export interface Explanation {
  text: string;
  summary: string;
  recommendations: string[];
  confidence: number;
  evidence_citations: string[];
  llm_model?: string;
  used_fallback: boolean;
  generated_at?: string;
}

// ─── Anomaly Detail ───

export interface AnomalyDetail {
  anomaly: Anomaly;
  root_cause?: RootCause;
  explanation?: Explanation;
}

// ─── API Response Types ───

export interface DatasetListResponse {
  datasets: Dataset[];
  total: number;
  page: number;
  per_page: number;
}

export interface AnomalyListResponse {
  anomalies: Anomaly[];
  summary: AnomalySummary;
  total: number;
  page: number;
  per_page: number;
}

export interface UploadResponse {
  dataset_id: string;
  name: string;
  status: string;
  row_count: number;
  column_count: number;
  anomalies_detected: number;
  message: string;
}

export type SeverityLevel = "critical" | "high" | "medium" | "low";

export function getSeverityLevel(severity: number): SeverityLevel {
  if (severity >= 0.7) return "critical";
  if (severity >= 0.4) return "high";
  if (severity >= 0.2) return "medium";
  return "low";
}

export function getSeverityColor(severity: number): string {
  if (severity >= 0.7) return "var(--color-critical)";
  if (severity >= 0.4) return "var(--color-high)";
  if (severity >= 0.2) return "var(--color-medium)";
  return "var(--color-low)";
}
