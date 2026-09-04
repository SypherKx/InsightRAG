import type { Anomaly, Dataset, SeverityCount, TypeCount, HealthStatus } from "@/types";

export const mockDatasets: Dataset[] = [
  {
    id: "ds_01",
    name: "clinical_vitals_icu_q4.csv",
    rows: 184_220,
    columns: 14,
    uploadedAt: "2025-05-20T14:22:00Z",
    anomalies: 27,
    status: "analyzed",
  },
  {
    id: "ds_02",
    name: "pubmed_pediatric_oncology.pdf",
    rows: 92_140,
    columns: 9,
    uploadedAt: "2025-05-19T09:10:00Z",
    anomalies: 12,
    status: "analyzed",
  },
  {
    id: "ds_03",
    name: "medical_lab_biomarkers.csv",
    rows: 1_204_002,
    columns: 22,
    uploadedAt: "2025-05-18T11:48:00Z",
    anomalies: 64,
    status: "analyzed",
  },
  {
    id: "ds_04",
    name: "curriculum_exam_performance.csv",
    rows: 14_002,
    columns: 11,
    uploadedAt: "2025-05-17T16:30:00Z",
    anomalies: 4,
    status: "analyzed",
  },
];

export const mockAnomalies: Anomaly[] = [
  {
    id: "an_001",
    datasetId: "ds_03",
    metric: "patient.blood_glucose",
    type: "spike",
    severity: "critical",
    score: 0.97,
    detectedAt: "2025-05-21T03:14:00Z",
    value: 340,
    expected: 110,
    delta: 230,
    summary:
      "Blood glucose spiked 3.1x baseline in Ward-4 ICU. FDA guideline contraindication cited.",
  },
  {
    id: "an_002",
    datasetId: "ds_01",
    metric: "vital.heart_rate_variability",
    type: "drop",
    severity: "high",
    score: 0.88,
    detectedAt: "2025-05-21T01:02:00Z",
    value: 24,
    expected: 65,
    delta: -41,
    summary:
      "Heart rate variability dropped 63% — correlates with post-op sedation protocol delta.",
  },
  {
    id: "an_003",
    datasetId: "ds_02",
    metric: "edu.exam_completion_rate",
    type: "deviation",
    severity: "high",
    score: 0.81,
    detectedAt: "2025-05-20T22:48:00Z",
    value: 41.2,
    expected: 88.4,
    delta: -47,
    summary: "Pathology Module 4 completion diverged from historical baseline cohort.",
  },
  {
    id: "an_004",
    datasetId: "ds_03",
    metric: "lab.creatinine_clearance",
    type: "spike",
    severity: "medium",
    score: 0.71,
    detectedAt: "2025-05-20T19:30:00Z",
    value: 2.8,
    expected: 1.1,
    delta: 1.7,
    summary: "Renal marker elevated in nephrology cohort B following dosage adjustment.",
  },
  {
    id: "an_005",
    datasetId: "ds_01",
    metric: "edu.student_engagement_score",
    type: "spike",
    severity: "medium",
    score: 0.69,
    detectedAt: "2025-05-20T15:05:00Z",
    value: 89,
    expected: 54,
    delta: 35,
    summary: "Interactive RAG study session boosted quiz scores in Anatomy 101.",
  },
  {
    id: "an_006",
    datasetId: "ds_04",
    metric: "patient.spO2_saturation",
    type: "deviation",
    severity: "low",
    score: 0.52,
    detectedAt: "2025-05-20T12:11:00Z",
    value: 92,
    expected: 98,
    delta: -6,
    summary: "Oxygen saturation drifted downward — protocol recommends O2 cannula check.",
  },
  {
    id: "an_007",
    datasetId: "ds_03",
    metric: "clinical.trial_retention_rate",
    type: "drop",
    severity: "critical",
    score: 0.94,
    detectedAt: "2025-05-21T04:01:00Z",
    value: 58,
    expected: 94,
    delta: -36,
    summary: "Phase-3 trial retention collapsed after dosage regimen modification.",
  },
  {
    id: "an_008",
    datasetId: "ds_02",
    metric: "academic.paper_citation_index",
    type: "drop",
    severity: "high",
    score: 0.85,
    detectedAt: "2025-05-20T08:22:00Z",
    value: 12,
    expected: 45,
    delta: -33,
    summary: "Research citation velocity dropped for unindexed journal entry.",
  },
];

export const severityDistribution: SeverityCount[] = [
  { severity: "critical", count: 14, color: "#FF5252" },
  { severity: "high", count: 28, color: "#FFB300" },
  { severity: "medium", count: 38, color: "#00D2FF" },
  { severity: "low", count: 22, color: "#00C853" },
];

export const typeDistribution: TypeCount[] = [
  { type: "Spike", count: 48, color: "#8C47D9" },
  { type: "Drop", count: 34, color: "#FF5252" },
  { type: "Deviation", count: 14, color: "#FFB300" },
  { type: "Trend", count: 6, color: "#00D2FF" },
];

export const timeseries = Array.from({ length: 48 }, (_, i) => {
  const base = 110 + Math.sin(i / 4) * 18 + Math.cos(i / 7) * 12;
  const noise = (Math.sin(i * 1.7) + 1) * 6;
  const spike = i === 36 ? 340 : i === 12 ? 280 : 0;
  return {
    t: `${String(i).padStart(2, "0")}:00`,
    value: Math.round(base + noise + spike),
    expected: Math.round(base),
  };
});

export const contributions = [
  { factor: "ward:icu_unit_4", weight: 0.45 },
  { factor: "protocol:paxlovid_dosage", weight: 0.28 },
  { factor: "cohort:pediatric_oncology", weight: 0.15 },
  { factor: "course:pathology_101", weight: 0.08 },
  { factor: "lab:serum_potassium", weight: 0.04 },
];

export const changePoints = [
  { t: "Mon", value: 110 },
  { t: "Tue", value: 114 },
  { t: "Wed", value: 118 },
  { t: "Thu", value: 122 },
  { t: "Fri", value: 340, marker: true },
  { t: "Sat", value: 180 },
  { t: "Sun", value: 130 },
];

export const mockHealth: HealthStatus = {
  api: "operational",
  rag: "operational",
  detector: "operational",
  uptime: 99.992,
};

export const queryResults = [
  {
    id: "q1",
    title: "Paxlovid contraindications in renal impairment",
    snippet:
      "According to FDA Clinical Guidelines Section 4.2: Dose adjustment is required for moderate renal impairment (eGFR 30–60 mL/min). Not recommended in severe renal impairment.",
    score: 0.96,
    ts: "1h ago",
  },
  {
    id: "q2",
    title: "Pediatric oncology protocol summary — Trial Phase 3",
    snippet:
      "Retrieved from PubMed Article #38291: Combination therapy demonstrated a 42% improvement in 3-year event-free survival rate in pediatric B-cell leukemia patients.",
    score: 0.92,
    ts: "4h ago",
  },
  {
    id: "q3",
    title: "Anatomy & Physiology 101 — Cardiac Action Potential",
    snippet:
      "Lecture Chapter 7: Phase 0 rapid depolarization occurs via voltage-gated Fast Na+ channels. Phase 2 plateau is mediated by L-type Slow Ca2+ channels.",
    score: 0.89,
    ts: "1d ago",
  },
  {
    id: "q4",
    title: "ICU Vitals Anomaly — Glucose Spike Protocol",
    snippet:
      "Clinical Protocol #88: Blood glucose readings exceeding 300 mg/dL require immediate IV insulin bolus and hourly potassium monitoring.",
    score: 0.85,
    ts: "1d ago",
  },
];
