import { createFileRoute, Link, useParams } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { ArrowLeft, Brain, CheckCircle2, GitBranch, Sparkles } from "lucide-react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
  ReferenceDot,
  Tooltip,
} from "recharts";
import { PageHeader } from "@/components/dashboard/DashboardShell";
import { GlassCard } from "@/components/premium/GlassCard";
import { GlowBadge } from "@/components/premium/GlowBadge";
import { getAnomalyDetail } from "../services/api";
import { getSeverityLevel } from "../types/backend-types";
import type { AnomalyDetail } from "../types/backend-types";
import { useEffect, useState } from "react";

export const Route = createFileRoute("/app/anomalies/$id")({
  head: () => ({ meta: [{ title: "Insight — InsightForge AI" }] }),
  component: InsightPage,
  notFoundComponent: () => <div className="p-10 text-zinc-400">Anomaly not found.</div>,
});

function InsightPage() {
  const { id } = useParams({ from: "/app/anomalies/$id" });
  const [detail, setDetail] = useState<AnomalyDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDetail() {
      try {
        setLoading(true);
        const res = await getAnomalyDetail(id);
        setDetail(res);
      } catch (error) {
        console.error("Error fetching anomaly detail:", error);
      } finally {
        setLoading(false);
      }
    }
    loadDetail();
  }, [id]);

  if (loading) {
    return (
      <>
        <PageHeader title="Loading anomaly details..." />
        <div className="px-6 py-8 md:px-10 grid gap-5 lg:grid-cols-2 animate-pulse">
          <div className="space-y-5">
            <GlassCard className="h-64 bg-white/[0.02]" />
            <GlassCard className="h-64 bg-white/[0.02]" />
          </div>
          <div className="space-y-5">
            <GlassCard className="h-96 bg-white/[0.02]" />
          </div>
        </div>
      </>
    );
  }

  if (!detail) {
    return (
      <div className="p-10 text-zinc-400 text-center">
        <p>Anomaly not found or failed to load.</p>
        <Link to="/app/anomalies" className="mt-4 inline-flex text-indigo-400 hover:underline">
          Back to explorer
        </Link>
      </div>
    );
  }

  const { anomaly: a, root_cause: rc, explanation: exp } = detail;
  const sevLevel = getSeverityLevel(a.severity);

  // Map drivers/contributions
  const contributionsList = (rc?.primary_drivers || []).map((driver) => ({
    factor: driver.segment,
    weight: driver.contribution / 100, // contribution is e.g. 45 for 45%
  }));

  // Generate a step-change visual for the change-point chart using before_mean and after_mean
  const cpData = rc?.change_point
    ? [
        { name: "Prior Day 2", value: rc.change_point.before_mean },
        { name: "Prior Day 1", value: rc.change_point.before_mean },
        { name: "Detection Point", value: rc.change_point.before_mean },
        { name: "Shift Day 1", value: rc.change_point.after_mean },
        { name: "Shift Day 2", value: rc.change_point.after_mean },
      ]
    : [
        { name: "Mon", value: a.value * 0.9 },
        { name: "Tue", value: a.value * 0.92 },
        { name: "Wed", value: a.value * 0.95 },
        { name: "Thu", value: a.value * 0.92 },
        { name: "Detection Point", value: a.value, marker: true },
        { name: "Sat", value: a.value * 0.8 },
        { name: "Sun", value: a.value * 0.75 },
      ];

  // Default fallback evidence
  const evidenceList =
    exp?.evidence_citations && exp.evidence_citations.length > 0
      ? exp.evidence_citations
      : [
          `Severity score: ${a.severity.toFixed(2)}`,
          `Confidence level: ${a.confidence.toFixed(1)}%`,
          `Observed value: ${a.value.toLocaleString()}`,
          rc?.methods_used?.length
            ? `Analyzed via: ${rc.methods_used.join(", ")}`
            : "Checked by multi-detector ensemble",
        ];

  return (
    <>
      <PageHeader
        title={a.metric}
        description={`Anomaly type: ${a.anomaly_type.toUpperCase()} | Severity: ${Math.round(a.severity * 100)}%`}
        action={
          <Link
            to="/app/anomalies"
            className="inline-flex items-center gap-1.5 text-sm text-zinc-400 hover:text-white transition"
          >
            <ArrowLeft className="h-4 w-4" /> Back to explorer
          </Link>
        }
      />

      <div className="px-6 py-8 md:px-10 grid gap-5 lg:grid-cols-2">
        {/* LEFT: Root cause */}
        <div className="flex flex-col gap-5">
          <GlassCard className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-medium text-white">
                <GitBranch className="h-4 w-4 text-indigo-300" /> Root Cause Analysis
              </div>
              <GlowBadge severity={sevLevel} />
            </div>
            <p className="mt-1 text-xs text-zinc-500">
              Contribution scoring across detected dimensions
            </p>
            {contributionsList.length > 0 ? (
              <ul className="mt-5 space-y-3">
                {contributionsList.map((c, i) => (
                  <motion.li
                    key={c.factor}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.08, duration: 0.6 }}
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-mono text-zinc-300">{c.factor}</span>
                      <span className="font-mono text-indigo-300">
                        {(c.weight * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/[0.05]">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${c.weight * 100}%` }}
                        transition={{
                          duration: 1,
                          delay: 0.1 + i * 0.08,
                          ease: [0.22, 1, 0.36, 1],
                        }}
                        className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 shadow-[0_0_12px_rgba(99,102,241,0.6)]"
                      />
                    </div>
                  </motion.li>
                ))}
              </ul>
            ) : (
              <div className="mt-5 text-sm text-zinc-500 text-center py-4">
                No segment drivers identified. Analysis was run overall.
              </div>
            )}
          </GlassCard>

          <GlassCard className="p-6">
            <div className="text-sm font-medium text-white">Change-point timeline</div>
            <p className="mt-1 text-xs text-zinc-500">
              {rc?.change_point
                ? `Detected shift (magnitude: ${Math.round(rc.change_point.change_magnitude * 100)}%) at detection window`
                : "Timeline distribution around detection point"}
            </p>
            <div className="mt-4 h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={cpData} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
                  <defs>
                    <linearGradient id="cp" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#ef4444" stopOpacity={0.5} />
                      <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="name"
                    stroke="#52525b"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis stroke="#52525b" fontSize={11} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{
                      background: "rgba(12,12,16,0.95)",
                      border: "1px solid rgba(255,255,255,0.08)",
                      borderRadius: 10,
                      fontSize: 12,
                    }}
                    itemStyle={{ color: "#fafafa" }}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="#f87171"
                    strokeWidth={2}
                    fill="url(#cp)"
                  />
                  <ReferenceDot
                    x="Detection Point"
                    y={rc?.change_point ? rc.change_point.before_mean : a.value}
                    r={6}
                    fill="#ef4444"
                    stroke="#fff"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </GlassCard>

          <GlassCard className="p-6">
            <div className="text-sm font-medium text-white">Evidence & Methodology</div>
            <ul className="mt-3 grid gap-2 text-xs text-zinc-400">
              {evidenceList.map((e, idx) => (
                <li
                  key={idx}
                  className="flex items-center gap-2 rounded-md border border-white/[0.05] bg-white/[0.02] px-3 py-2 font-mono"
                >
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> {e}
                </li>
              ))}
            </ul>
          </GlassCard>
        </div>

        {/* RIGHT: AI Explanation */}
        <div className="flex flex-col gap-5">
          <GlassCard gradientBorder className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-medium text-white">
                <Brain className="h-4 w-4 text-indigo-300" /> AI Explanation Console
              </div>
              <span className="font-mono text-[10px] text-indigo-300">
                {exp?.llm_model || "forge-analyst-v3"} · conf {a.confidence.toFixed(0)}%
              </span>
            </div>

            <div className="mt-4 space-y-3">
              <motion.p
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2, duration: 0.7 }}
                className="text-sm leading-relaxed text-zinc-200"
              >
                {exp?.text || rc?.hypothesis || "No text explanation available."}
              </motion.p>
              {exp?.summary && (
                <motion.p
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4, duration: 0.7 }}
                  className="text-sm leading-relaxed text-zinc-400 border-l-2 border-indigo-500/50 pl-3 italic"
                >
                  {exp.summary}
                </motion.p>
              )}
            </div>

            {exp?.recommendations && exp.recommendations.length > 0 && (
              <div className="mt-5 border-t border-white/[0.06] pt-4">
                <div className="text-[11px] uppercase tracking-[0.15em] text-zinc-500">
                  Recommendations
                </div>
                <ul className="mt-3 space-y-2 text-sm">
                  {exp.recommendations.map((r, idx) => (
                    <li key={idx} className="flex items-start gap-2.5 text-zinc-300">
                      <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-indigo-400 shadow-[0_0_8px_rgba(99,102,241,0.8)]" />{" "}
                      {r}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </GlassCard>

          {exp?.evidence_citations && exp.evidence_citations.length > 0 && (
            <GlassCard className="p-6">
              <div className="flex items-center gap-2 text-sm font-medium text-white">
                <Sparkles className="h-4 w-4 text-violet-300" /> Citations & Grounding
              </div>
              <div className="mt-3 grid gap-2 text-xs text-zinc-400 font-mono">
                {exp.evidence_citations.map((cite, idx) => (
                  <div
                    key={idx}
                    className="rounded-md border border-white/[0.05] bg-white/[0.02] px-3 py-2"
                  >
                    {cite}
                  </div>
                ))}
              </div>
            </GlassCard>
          )}
        </div>
      </div>
    </>
  );
}
