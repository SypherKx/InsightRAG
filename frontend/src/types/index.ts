export type Severity = "critical" | "high" | "medium" | "low";
export type AnomalyType = "spike" | "drop" | "deviation" | "trend";

export interface Anomaly {
  id: string;
  datasetId: string;
  metric: string;
  type: AnomalyType;
  severity: Severity;
  score: number;
  detectedAt: string;
  value: number;
  expected: number;
  delta: number;
  summary: string;
}

export interface Dataset {
  id: string;
  name: string;
  rows: number;
  columns: number;
  uploadedAt: string;
  anomalies: number;
  status: "analyzing" | "analyzed" | "failed";
}

export interface SeverityCount {
  severity: Severity;
  count: number;
  color: string;
}
export interface TypeCount {
  type: string;
  count: number;
  color: string;
}

export interface HealthStatus {
  api: "operational" | "degraded" | "down";
  rag: "operational" | "degraded" | "down";
  detector: "operational" | "degraded" | "down";
  uptime: number;
}
