import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Activity,
  AlertTriangle,
  FileText,
  Search,
  Upload,
  ShieldCheck,
  Sparkles,
  Plus,
} from "lucide-react";
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PageHeader } from "@/components/dashboard/DashboardShell";
import { GlassCard } from "@/components/premium/GlassCard";
import { GlowBadge } from "@/components/premium/GlowBadge";
import { PremiumButton } from "@/components/premium/PremiumButton";
import { getDatasets, getRAGStats, getAnomalies } from "../services/api";
import { useEffect, useState } from "react";

export const Route = createFileRoute("/app/dashboard")({
  head: () => ({ meta: [{ title: "Clinical & Educational RAG Cockpit — InsightForge" }] }),
  component: DashboardPage,
});

export function DashboardPage() {
  const [datasetsList, setDatasetsList] = useState<any[]>([]);
  const [anomaliesList, setAnomaliesList] = useState<any[]>([]);
  const [totalVectors, setTotalVectors] = useState<number>(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadRealData() {
      setLoading(true);
      try {
        const [dsRes, ragRes] = await Promise.allSettled([getDatasets(1, 20), getRAGStats()]);

        if (!isMounted) return;

        let realDatasets: any[] = [];
        if (dsRes.status === "fulfilled" && dsRes.value && Array.isArray(dsRes.value.datasets)) {
          realDatasets = dsRes.value.datasets;
          setDatasetsList(realDatasets);
        }

        if (ragRes.status === "fulfilled" && ragRes.value) {
          setTotalVectors(ragRes.value.total_vectors || 0);
        }

        // If datasets exist, fetch anomalies for the latest dataset
        if (realDatasets.length > 0) {
          try {
            const latestDsId = realDatasets[0].id;
            const anomRes = await getAnomalies(latestDsId, { per_page: 50 });
            if (isMounted && anomRes && Array.isArray(anomRes.anomalies)) {
              setAnomaliesList(anomRes.anomalies);
            }
          } catch (e) {
            console.log("Could not load anomalies for dataset", e);
          }
        }
      } catch (err) {
        console.error("Error loading cockpit data:", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadRealData();
    return () => {
      isMounted = false;
    };
  }, []);

  // Compute real dynamic chart breakdown from real anomalies
  const severityCounts = { critical: 0, high: 0, medium: 0, low: 0 };
  const typeCounts = { spike: 0, drop: 0, deviation: 0, trend: 0 };

  anomaliesList.forEach((a) => {
    const sev = (
      a.severity_level || (a.severity >= 0.8 ? "critical" : a.severity >= 0.5 ? "high" : "medium")
    ).toLowerCase();
    if (sev in severityCounts) severityCounts[sev as keyof typeof severityCounts]++;
    else severityCounts.high++;

    const typ = (a.anomaly_type || "spike").toLowerCase();
    if (typ in typeCounts) typeCounts[typ as keyof typeof typeCounts]++;
    else typeCounts.spike++;
  });

  const realSeverityData = [
    { severity: "Critical", count: severityCounts.critical, color: "#aa2d00" },
    { severity: "High", count: severityCounts.high, color: "#f59e0b" },
    { severity: "Medium", count: severityCounts.medium, color: "#3b82f6" },
    { severity: "Low", count: severityCounts.low, color: "#10b981" },
  ].filter((d) => d.count > 0 || anomaliesList.length === 0);

  const realTypeData = [
    { type: "Spike", count: typeCounts.spike },
    { type: "Drop", count: typeCounts.drop },
    { type: "Deviation", count: typeCounts.deviation },
    { type: "Trend", count: typeCounts.trend },
  ];

  return (
    <>
      <PageHeader
        title="Clinical & Educational RAG Cockpit"
        description="Monitor patient vitals anomalies, PubMed medical search, and academic lecture RAG indices."
        action={
          <div className="flex items-center gap-3">
            <Link to="/app/query">
              <PremiumButton variant="outlineOnDark" size="sm">
                <Search className="h-4 w-4" /> Query RAG
              </PremiumButton>
            </Link>
            <Link to="/app/upload">
              <PremiumButton variant="primaryPill" size="sm">
                <Upload className="h-4 w-4" /> Upload Dataset / PDF
              </PremiumButton>
            </Link>
          </div>
        }
      />

      <div className="p-6 md:p-8 space-y-8 bg-[var(--canvas)] min-h-screen text-[var(--ink)] transition-colors duration-300">
        {/* 1. TOP METRIC STAT CARDS */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <GlassCard
            variant="canvas"
            className="p-5 border border-[var(--hairline)] shadow-sm bg-[var(--surface-card)]"
          >
            <div className="flex items-center justify-between">
              <span className="caption text-xs uppercase font-semibold text-[var(--muted)]">
                Active Datasets
              </span>
              <FileText className="h-4 w-4 text-[#c1fbd4]" />
            </div>
            <div className="mt-3 text-3xl font-bold text-[var(--ink)]">{datasetsList.length}</div>
            <div className="mt-1 text-xs text-[var(--muted)]">Uploaded Files</div>
          </GlassCard>

          <GlassCard
            variant="canvas"
            className="p-5 border border-[var(--hairline)] shadow-sm bg-[var(--surface-card)]"
          >
            <div className="flex items-center justify-between">
              <span className="caption text-xs uppercase font-semibold text-[var(--muted)]">
                Detected Anomalies
              </span>
              <AlertTriangle className="h-4 w-4 text-[#aa2d00]" />
            </div>
            <div className="mt-3 text-3xl font-bold text-[var(--ink)]">{anomaliesList.length}</div>
            <div className="mt-1 text-xs text-[#aa2d00] font-semibold">
              {severityCounts.critical > 0
                ? `${severityCounts.critical} Critical Spikes`
                : "Live Backend Signals"}
            </div>
          </GlassCard>

          <GlassCard
            variant="canvas"
            className="p-5 border border-[var(--hairline)] shadow-sm bg-[var(--surface-card)]"
          >
            <div className="flex items-center justify-between">
              <span className="caption text-xs uppercase font-semibold text-[var(--muted)]">
                FAISS Vectors Indexed
              </span>
              <Sparkles className="h-4 w-4 text-[#c1fbd4]" />
            </div>
            <div className="mt-3 text-3xl font-bold text-[var(--ink)]">
              {totalVectors.toLocaleString()}
            </div>
            <div className="mt-1 text-xs text-[#c1fbd4] font-semibold">100% Local Privacy</div>
          </GlassCard>

          <GlassCard
            variant="canvas"
            className="p-5 border border-[var(--hairline)] shadow-sm bg-[var(--surface-card)]"
          >
            <div className="flex items-center justify-between">
              <span className="caption text-xs uppercase font-semibold text-[var(--muted)]">
                RAG Engine Status
              </span>
              <ShieldCheck className="h-4 w-4 text-[#c1fbd4]" />
            </div>
            <div className="mt-3 text-3xl font-bold text-[var(--ink)]">
              {totalVectors > 0 ? "Active" : "Ready"}
            </div>
            <div className="mt-1 text-xs text-[var(--muted)]">Page & Paragraph Citation</div>
          </GlassCard>
        </div>

        {/* 2. CHARTS OVERVIEW */}
        <div className="grid gap-6 lg:grid-cols-2 min-w-0">
          {/* Severity Distribution */}
          <GlassCard
            variant="canvas"
            className="p-6 border border-[var(--hairline)] shadow-sm bg-[var(--surface-card)] min-w-0"
          >
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="heading-sm font-semibold text-[var(--ink)]">
                  Clinical Severity Distribution
                </h3>
                <p className="caption text-xs text-[var(--muted)]">
                  Breakdown of patient vital & academic metric alerts
                </p>
              </div>
              <GlowBadge variant="mint">REALTIME</GlowBadge>
            </div>
            <div className="h-[220px] w-full min-w-0">
              <ResponsiveContainer debounce={50} width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={realSeverityData}
                    dataKey="count"
                    nameKey="severity"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={4}
                  >
                    {realSeverityData.map((s, idx) => (
                      <Cell key={idx} fill={s.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </GlassCard>

          {/* Anomaly Types */}
          <GlassCard
            variant="canvas"
            className="p-6 border border-[var(--hairline)] shadow-sm bg-[var(--surface-card)] min-w-0"
          >
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="heading-sm font-semibold text-[var(--ink)]">
                  Anomaly Detection Classes
                </h3>
                <p className="caption text-xs text-[var(--muted)]">
                  Spike, Drop, and Change-Point counts
                </p>
              </div>
              <GlowBadge variant="shade">STATISTICAL</GlowBadge>
            </div>
            <div className="h-[220px] w-full min-w-0">
              <ResponsiveContainer debounce={50} width="100%" height={220}>
                <BarChart data={realTypeData} margin={{ left: 10, right: 10 }}>
                  <XAxis dataKey="type" stroke="#9dabad" fontSize={12} />
                  <YAxis stroke="#9dabad" fontSize={12} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#c1fbd4" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </GlassCard>
        </div>

        {/* 3. RECENT ANOMALIES / DATASETS TABLE */}
        <GlassCard
          variant="canvas"
          className="p-6 border border-[var(--hairline)] shadow-sm bg-[var(--surface-card)]"
        >
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="heading-md font-semibold text-[var(--ink)]">
                Recent Datasets & Health Signals
              </h3>
              <p className="caption text-xs text-[var(--muted)]">
                Real-time telemetry and uploaded files
              </p>
            </div>
            <Link to="/app/upload">
              <PremiumButton variant="outlineOnDark" size="sm">
                <Plus className="h-4 w-4" /> Add Dataset
              </PremiumButton>
            </Link>
          </div>

          {datasetsList.length === 0 ? (
            <div className="py-12 text-center text-[var(--muted)] space-y-3">
              <Activity className="h-10 w-10 mx-auto opacity-40 text-[#c1fbd4]" />
              <p className="text-sm font-medium">No datasets uploaded yet.</p>
              <p className="text-xs max-w-md mx-auto">
                Upload a medical CSV or PDF document to start automatic anomaly detection & vector
                indexing.
              </p>
              <Link to="/app/upload" className="inline-block mt-2">
                <PremiumButton variant="primaryPill" size="sm">
                  Upload First Dataset
                </PremiumButton>
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className="border-b border-[var(--hairline)] text-xs text-[var(--muted)] uppercase tracking-wider">
                    <th className="py-3 px-4">Dataset Name</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Rows / Size</th>
                    <th className="py-3 px-4">Anomalies</th>
                    <th className="py-3 px-4">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--hairline)]">
                  {datasetsList.map((ds) => (
                    <tr key={ds.id} className="hover:bg-[var(--surface-soft)] transition-colors">
                      <td className="py-3 px-4 font-medium text-[var(--ink)]">{ds.name}</td>
                      <td className="py-3 px-4">
                        <GlowBadge
                          variant={
                            ds.status === "completed" || ds.status === "analyzed" ? "mint" : "shade"
                          }
                        >
                          {ds.status || "analyzed"}
                        </GlowBadge>
                      </td>
                      <td className="py-3 px-4 text-[var(--muted)]">
                        {ds.row_count || ds.rows || 0}
                      </td>
                      <td className="py-3 px-4 font-semibold text-[#aa2d00]">
                        {ds.anomalies_detected || ds.anomalies || 0}
                      </td>
                      <td className="py-3 px-4">
                        <Link to="/app/query" className="text-xs text-[#c1fbd4] hover:underline">
                          Query RAG &rarr;
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </GlassCard>
      </div>
    </>
  );
}
