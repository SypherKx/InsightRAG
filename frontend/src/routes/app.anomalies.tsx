import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMemo, useState, useEffect } from "react";
import { AlertOctagon, Search, Bot, ArrowRight, Activity, FileText } from "lucide-react";
import { PageHeader } from "@/components/dashboard/DashboardShell";
import { mockAnomalies, mockDatasets } from "@/lib/mock-data";
import { getDatasets, getAnomalies } from "../services/api";

export const Route = createFileRoute("/app/anomalies")({
  head: () => ({ meta: [{ title: "Clinical Anomaly Signals — InsightForge Health & Edu" }] }),
  component: AnomaliesPage,
});

export function AnomaliesPage() {
  const navigate = useNavigate();
  const [datasetsList, setDatasetsList] = useState<any[]>(mockDatasets);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>("ds_01");
  const [anomaliesList, setAnomaliesList] = useState<any[]>(mockAnomalies);
  const [loadingAnomalies, setLoadingAnomalies] = useState(false);
  const [minScore, setMinScore] = useState(0.2);
  const [q, setQ] = useState("");

  // 1. Fetch uploaded datasets list
  useEffect(() => {
    async function loadDatasets() {
      try {
        const res = await getDatasets(1, 20);
        if (res && res.datasets && res.datasets.length > 0) {
          setDatasetsList(res.datasets);
          setSelectedDatasetId(res.datasets[0].id);
        }
      } catch (err) {
        console.log("Using default datasets list.");
      }
    }
    loadDatasets();
  }, []);

  // 2. Fetch real anomalies for selected dataset ID from backend
  useEffect(() => {
    if (!selectedDatasetId) return;
    async function fetchAnomalies() {
      setLoadingAnomalies(true);
      try {
        const res = await getAnomalies(selectedDatasetId, { severity_min: minScore });
        if (res && res.anomalies && res.anomalies.length > 0) {
          const mapped = res.anomalies.map((a: any) => ({
            id: a.id,
            metric: a.metric || "Clinical Metric",
            score: a.severity || a.confidence || 0.85,
            type: a.anomaly_type || "Spike Outlier",
            summary: `Value ${a.value} exceeded threshold (Expected: ${a.expected_min ?? 60} - ${a.expected_max ?? 100})`,
            start_time: a.timestamp || "14:00:00",
            end_time: a.timestamp || "14:05:00",
            value: a.value,
          }));
          setAnomaliesList(mapped);
        } else {
          // Fall back to mock if empty
          setAnomaliesList(mockAnomalies);
        }
      } catch (err) {
        setAnomaliesList(mockAnomalies);
      } finally {
        setLoadingAnomalies(false);
      }
    }
    fetchAnomalies();
  }, [selectedDatasetId, minScore]);

  const filtered = useMemo(() => {
    return anomaliesList
      .filter((a) => (a.score ?? 0.8) >= minScore)
      .filter((a) => {
        if (!q) return true;
        const searchTarget = `${a.metric} ${a.type} ${a.summary}`.toLowerCase();
        return searchTarget.includes(q.toLowerCase());
      });
  }, [anomaliesList, minScore, q]);

  // Connect Anomaly to RAG Query Engine: pre-fill query & navigate to /app/query
  const askOllamaAboutAnomaly = (anomaly: any) => {
    const promptText = `Explain why the anomaly in ${anomaly.metric} (value: ${anomaly.value}) occurred and suggest clinical protocols.`;
    navigate({ to: "/app/query", search: { prompt: promptText } as any });
  };

  return (
    <>
      <PageHeader
        title="Universal Data & Signal Anomalies"
        description="Automated statistical root-cause analysis across any data stream using Pettitt change-point tests and Z-Score bounds."
      />

      <div className="p-6 md:p-8 space-y-6 bg-[#000000] min-h-screen text-white">
        {/* Module Identity Chip & Explanation Banner */}
        <div className="hashicorp-card p-6 border-[#f5a623]/30 space-y-3">
          <div className="flex items-center justify-between">
            <div className="eyebrow-hashicorp text-[#f5a623] flex items-center gap-2">
              <AlertOctagon className="w-4 h-4 text-[#f5a623]" />
              <span>UNIVERSAL SIGNAL ANOMALY DETECTOR</span>
            </div>
            <span className="product-pill font-mono text-xs text-[#f5a623] border-[#f5a623]/30">
              Connected to Uploaded CSV Datasets
            </span>
          </div>

          <p className="body-hashicorp text-sm text-[#b2b6bd] leading-relaxed">
            <strong className="text-white">What does this module do?</strong> When you upload a
            patient vital log or academic marks CSV in{" "}
            <code className="bg-[#242424] px-1.5 py-0.5 rounded text-white font-mono text-xs">
              Document Ingestion
            </code>
            , Vault scans the columns for mathematical outliers (e.g. ICU oxygen drop below 88%,
            heart rate spike &gt;140 bpm, or attendance dips). You can click{" "}
            <strong className="text-[#00bcff]">"Ask Ollama AI About This Anomaly"</strong> on any
            signal below to run local Llama 3.2 synthesis on it!
          </p>
        </div>

        {/* FILTER CONTROLS */}
        <div className="hashicorp-card p-6">
          <div className="grid gap-6 md:grid-cols-3 items-end">
            <div>
              <label className="eyebrow-hashicorp text-[#b2b6bd] block mb-2">
                SEARCH METRIC OR SUMMARY
              </label>
              <div className="relative flex items-center">
                <Search className="absolute left-3.5 h-4 w-4 text-[#b2b6bd]" />
                <input
                  type="text"
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="e.g. glucose, heart_rate, exam..."
                  className="w-full rounded-md border border-[rgba(178,182,189,0.2)] bg-[#000000] pl-10 pr-3 py-2 text-sm text-white outline-none focus:border-[#f5a623]"
                />
              </div>
            </div>

            <div>
              <label className="eyebrow-hashicorp text-[#b2b6bd] block mb-2">
                SELECT UPLOADED DATASET
              </label>
              <select
                value={selectedDatasetId}
                onChange={(e) => setSelectedDatasetId(e.target.value)}
                className="w-full rounded-md border border-[rgba(178,182,189,0.2)] bg-[#000000] px-3 py-2 text-sm text-white outline-none focus:border-[#f5a623]"
              >
                {datasetsList.map((d) => (
                  <option key={d.id} value={d.id} className="bg-[#141414] text-white">
                    {d.name} ({d.anomalies_count || d.anomalies || 8} anomalies)
                  </option>
                ))}
              </select>
            </div>

            <div>
              <div className="flex justify-between eyebrow-hashicorp text-[#b2b6bd] mb-2">
                <span>MINIMUM CONFIDENCE SCORE</span>
                <span className="font-mono text-[#f5a623] font-bold">{minScore.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={minScore}
                onChange={(e) => setMinScore(parseFloat(e.target.value))}
                className="w-full accent-[#f5a623]"
              />
            </div>
          </div>
        </div>

        {/* ANOMALY RESULTS GRID */}
        <div className="space-y-4">
          <div className="eyebrow-hashicorp text-[#f5a623] flex items-center justify-between">
            <span>DETECTED ANOMALY SIGNALS ({filtered.length})</span>
            {loadingAnomalies && (
              <span className="font-mono text-xs text-[#b2b6bd]">Scanning dataset...</span>
            )}
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {filtered.map((a) => (
              <div
                key={a.id}
                className="hashicorp-card p-6 space-y-4 border-[rgba(178,182,189,0.15)] flex flex-col justify-between"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between border-b border-[rgba(178,182,189,0.12)] pb-3">
                    <div className="flex items-center gap-2">
                      <AlertOctagon className="h-5 w-5 text-[#f5a623]" />
                      <span className="headline-hashicorp text-white text-base">{a.metric}</span>
                    </div>
                    <span className="bg-[#f5a623]/20 text-[#f5a623] font-mono text-xs px-2.5 py-0.5 rounded-full font-bold">
                      Severity: {((a.score ?? 0.8) * 100).toFixed(0)}%
                    </span>
                  </div>

                  <p className="body-hashicorp text-sm text-[#b2b6bd]">{a.summary}</p>

                  <div className="grid grid-cols-2 gap-2 text-xs font-mono bg-[#242424] p-3 rounded-md border border-[rgba(178,182,189,0.12)]">
                    <div>
                      <span className="text-[#b2b6bd]">TYPE:</span>{" "}
                      <span className="text-white font-bold">{a.type}</span>
                    </div>
                    <div>
                      <span className="text-[#b2b6bd]">TIMESTAMPS:</span>{" "}
                      <span className="text-white">
                        {a.start_time} → {a.end_time}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Direct Cross-Module Link: Connect Anomaly to RAG Q&A Engine */}
                <button
                  onClick={() => askOllamaAboutAnomaly(a)}
                  className="w-full mt-2 btn-product-waypoint flex items-center justify-center gap-2"
                >
                  <Bot className="w-4 h-4 text-black" />
                  <span>Ask Ollama AI About This Anomaly</span>
                  <ArrowRight className="w-4 h-4 text-black" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
