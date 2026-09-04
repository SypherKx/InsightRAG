import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Sparkles,
  CheckCircle2,
  FileText,
  Activity,
  ArrowRight,
  ShieldCheck,
  Cpu,
} from "lucide-react";

const sampleQueries = [
  {
    id: "q1",
    label: "Paxlovid renal dosage",
    question: "What is the recommended Paxlovid dosage for moderate renal impairment?",
    doc: "FDA Clinical Guidelines 2025.pdf",
    page: "Page 14, Sec 4.2",
    score: 99.4,
    answer:
      "Administer 150 mg nirmatrelvir (one 150 mg tablet) and 100 mg ritonavir (one 100 mg tablet) together twice daily for 5 days.",
    tag: "FDA GUIDELINE",
  },
  {
    id: "q2",
    label: "Pediatric leukemia trial",
    question: "What were the Phase 3 trial survival outcomes in pediatric B-cell leukemia?",
    doc: "PubMed_Article_38291.pdf",
    page: "Page 8, Table 3",
    score: 98.8,
    answer:
      "Combination immunotherapy demonstrated a 42% improvement in 3-year event-free survival rate compared to standard chemotherapy.",
    tag: "PUBMED RESEARCH",
  },
  {
    id: "q3",
    label: "Anatomy 101 action potential",
    question: "Explain Phase 0 and Phase 2 of the cardiac action potential.",
    doc: "Medical_Physiology_Textbook.pdf",
    page: "Chapter 7, Page 142",
    score: 97.5,
    answer:
      "Phase 0 rapid depolarization is mediated by voltage-gated Fast Na+ channels. Phase 2 plateau is sustained by inward L-type Ca2+ current.",
    tag: "UNIVERSITY SYLLABUS",
  },
];

export function HeroVisual() {
  const [activeIdx, setActiveIdx] = useState(0);
  const activeItem = sampleQueries[activeIdx];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.6 }}
      className="relative w-full flex flex-col gap-3"
    >
      {/* 1. PROFESSIONAL SAAS DASHBOARD UI MOCKUP CONTAINER */}
      <div className="relative rounded-xl border border-[var(--hairline)] overflow-hidden shadow-2xl bg-[var(--surface-card)] group">
        <img
          src="/professional_dashboard.jpg"
          alt="InsightForge AI Clinical Intelligence Dashboard"
          className="w-full h-[220px] sm:h-[260px] md:h-[280px] object-cover object-top transform transition-transform duration-500 group-hover:scale-102"
        />

        {/* Ambient Dark Gradient Scrim Overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-[var(--canvas)] via-transparent to-transparent pointer-events-none" />

        {/* Floating Glassmorphism Badges over Dashboard */}
        <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none">
          <div className="backdrop-blur-md bg-black/70 border border-white/20 px-3 py-1 rounded-full text-[11px] font-medium text-white flex items-center gap-1.5 shadow-md">
            <Sparkles className="h-3 w-3 text-[#c1fbd4]" />
            <span className="font-mono text-[10px] uppercase tracking-wider">
              384-D FAISS VECTOR FORGE
            </span>
          </div>

          <div className="backdrop-blur-md bg-black/70 border border-white/20 px-3 py-1 rounded-full text-[11px] font-medium text-[#c1fbd4] flex items-center gap-1 shadow-md">
            <ShieldCheck className="h-3 w-3 text-[#c1fbd4]" />
            <span className="font-mono text-[10px] uppercase tracking-wider">
              100% LOCAL PRIVACY
            </span>
          </div>
        </div>
      </div>

      {/* 2. COMPACT LIVE INTERACTIVE QUERY PREVIEW BOX */}
      <div className="rounded-xl border border-[var(--hairline)] bg-[var(--surface-card)] p-4 shadow-lg">
        {/* Sample Question Selector */}
        <div className="mb-2 flex items-center justify-between">
          <span className="eyebrow-cap text-[10px] text-[var(--muted)]">INTERACTIVE DEMO:</span>
          <span className="text-[10px] font-mono text-[#c1fbd4] font-semibold">
            FAISS RAG ACTIVE
          </span>
        </div>

        <div className="flex flex-wrap gap-1.5 mb-3">
          {sampleQueries.map((item, idx) => (
            <button
              key={item.id}
              onClick={() => setActiveIdx(idx)}
              className={`text-[11px] px-2.5 py-1 rounded-full font-medium transition-all cursor-pointer ${
                activeIdx === idx
                  ? "bg-[#c1fbd4] text-[#000000] font-semibold scale-105"
                  : "bg-[var(--surface-soft)] text-[var(--ink)] border border-[var(--hairline)] hover:border-[#c1fbd4]"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Query Input Box */}
        <div className="relative flex items-center rounded-lg border border-[var(--hairline)] bg-[var(--surface-soft)] px-3 py-2 shadow-inner mb-3">
          <Search className="h-3.5 w-3.5 text-[#c1fbd4] mr-2 shrink-0" />
          <span className="text-xs font-medium text-[var(--ink)] truncate">
            {activeItem.question}
          </span>
        </div>

        {/* Animated Answer Card */}
        <AnimatePresence mode="wait">
          <motion.div
            key={activeItem.id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2 }}
            className="rounded-lg border border-[var(--hairline)] bg-[var(--surface-soft)] p-3 space-y-2"
          >
            <div className="flex items-center justify-between border-b border-[var(--hairline)] pb-2">
              <div className="flex items-center gap-1.5 truncate">
                <FileText className="h-3.5 w-3.5 text-[#c1fbd4] shrink-0" />
                <span className="text-xs font-semibold text-[var(--ink)] truncate">
                  {activeItem.doc}
                </span>
              </div>
              <span className="text-[11px] font-mono font-bold text-[#c1fbd4] shrink-0">
                {activeItem.score}% Match
              </span>
            </div>

            <p className="text-xs text-[var(--body)] leading-relaxed">"{activeItem.answer}"</p>
          </motion.div>
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
