import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Copy,
  Check,
  Terminal,
  Cpu,
  Shield,
  Layers,
  Sparkles,
  BookOpen,
  Code,
  ArrowRight,
  ArrowLeft,
  Box,
  FileText,
  Search,
  ExternalLink,
  Zap,
  HardDrive,
  Lock,
  MessageSquare,
  Sliders,
  Scissors,
  CheckCircle2,
  ChevronRight,
  LayoutGrid,
  ListFilter,
  Eye,
  RefreshCw,
} from "lucide-react";

export const Route = createFileRoute("/docs")({
  head: () => ({
    meta: [
      { title: "Documentation" },
      {
        name: "description",
        content:
          "Lean, step-by-step documentation for InsightRAG: 1-Line Quickstart, Deep Multimodal Ingestion, Fullscreen Studio, Conversational Memory, Dual Compute, Security Hardening, Standalone Export, and REST API.",
      },
    ],
  }),
  component: DocsPage,
});

// All 8 Core Documentation Chapters
const chapters = [
  {
    id: "quickstart",
    title: "1-Line Setup & Launch",
    short: "Quickstart",
    category: "Getting Started",
    icon: Terminal,
    color: "#ffe600",
    summary: "Get InsightRAG running in seconds with a single command or 1-word offline launcher.",
  },
  {
    id: "ingestion",
    title: "Deep Ingestion & Visual ROI",
    short: "Deep Ingestion",
    category: "Core Engine",
    icon: Sparkles,
    color: "#ec4899",
    summary: "Systematic page-by-page comprehension, 30px vector drawings, 200 DPI OCR, and diagram auto-cropping.",
  },
  {
    id: "studio",
    title: "Fullscreen Studio & Memory",
    short: "Studio & Memory",
    category: "User Experience",
    icon: MessageSquare,
    color: "#8b5cf6",
    summary: "Two-phase workflow, multi-turn conversational context, zoomable diagram cards, and session persistence.",
  },
  {
    id: "slicing",
    title: "Selective Page Slicing",
    short: "Page Slicing",
    category: "Optimization",
    icon: Scissors,
    color: "#3b82f6",
    summary: "Slice and index only the exact chapters you need from 1,000+ page books with zero vector bloat.",
  },
  {
    id: "compute",
    title: "Dual Compute & Embeddings",
    short: "Compute & Models",
    category: "Intelligence",
    icon: Cpu,
    color: "#10b981",
    summary: "100% air-gapped local Ollama vs. Turbo Cloud (Groq, Gemini, OpenAI) + speed-tiered embeddings.",
  },
  {
    id: "security",
    title: "Enterprise Hardening",
    short: "Security & Privacy",
    category: "Security",
    icon: Shield,
    color: "#f59e0b",
    summary: "OWASP headers, path traversal sanitation, decompression bomb limits, and prompt jailbreak isolation.",
  },
  {
    id: "standalone",
    title: "Standalone Turnkey Export",
    short: "ZIP Export",
    category: "Deployment",
    icon: Box,
    color: "#06b6d4",
    summary: "Export a self-contained ZIP bundle with pre-indexed vectors and 1-click launchers for any PC.",
  },
  {
    id: "api",
    title: "Developer REST API",
    short: "REST API",
    category: "Developers",
    icon: Code,
    color: "#6366f1",
    summary: "Standard HTTP endpoints to integrate InsightRAG directly into your custom apps, bots, or scripts.",
  },
];

function DocsPage() {
  const [activeChapterIndex, setActiveChapterIndex] = useState(0);
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"slide" | "continuous">("slide");
  const [slideDirection, setSlideDirection] = useState<1 | -1>(1);

  const activeChapter = chapters[activeChapterIndex];

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCmd(id);
    setTimeout(() => setCopiedCmd(null), 2000);
  };

  const handleSelectChapter = (index: number) => {
    setSlideDirection(index > activeChapterIndex ? 1 : -1);
    setActiveChapterIndex(index);
    if (viewMode === "continuous") {
      const el = document.getElementById(chapters[index].id);
      if (el) {
        const offset = 90;
        const top = el.getBoundingClientRect().top + window.pageYOffset - offset;
        window.scrollTo({ top, behavior: "smooth" });
      }
    } else {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handleNext = () => {
    if (activeChapterIndex < chapters.length - 1) {
      handleSelectChapter(activeChapterIndex + 1);
    }
  };

  const handlePrev = () => {
    if (activeChapterIndex > 0) {
      handleSelectChapter(activeChapterIndex - 1);
    }
  };

  // Keyboard navigation for smooth slide experience (Left/Right arrow)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input
      if (["INPUT", "TEXTAREA"].includes((e.target as HTMLElement).tagName)) return;
      if (e.key === "ArrowRight") {
        handleNext();
      } else if (e.key === "ArrowLeft") {
        handlePrev();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeChapterIndex, viewMode]);

  // ScrollSpy for continuous mode
  useEffect(() => {
    if (viewMode !== "continuous") return;
    const handleScroll = () => {
      const scrollPos = window.scrollY + 140;
      for (let i = chapters.length - 1; i >= 0; i--) {
        const el = document.getElementById(chapters[i].id);
        if (el && el.offsetTop <= scrollPos) {
          setActiveChapterIndex(i);
          break;
        }
      }
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, [viewMode]);

  // Group chapters by category for navigation
  const categories = Array.from(new Set(chapters.map((c) => c.category)));

  // Smooth slide motion variants
  const slideVariants = {
    enter: (direction: number) => ({
      x: direction > 0 ? 40 : -40,
      opacity: 0,
      filter: "blur(4px)",
    }),
    center: {
      x: 0,
      opacity: 1,
      filter: "blur(0px)",
      transition: {
        x: { type: "spring", stiffness: 350, damping: 30 },
        opacity: { duration: 0.25 },
        filter: { duration: 0.2 },
      },
    },
    exit: (direction: number) => ({
      x: direction > 0 ? -40 : 40,
      opacity: 0,
      filter: "blur(4px)",
      transition: {
        x: { type: "spring", stiffness: 350, damping: 30 },
        opacity: { duration: 0.2 },
      },
    }),
  };

  return (
    <div className="min-h-screen bg-[#f4f4f0] text-black font-sans selection:bg-[#ffe600] selection:text-black">
      {/* Top Banner & Header */}
      <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b-4 border-black px-4 sm:px-8 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="bg-[#ffe600] text-black hover:bg-yellow-400 font-black font-mono text-base sm:text-lg px-3 py-1 rounded-xl border-2 border-black shadow-[2px_2px_0px_#000] italic tracking-tighter transition-transform active:scale-95"
            >
              InsightRAG
            </Link>
            <span className="hidden sm:inline-block bg-black text-[#ffe600] font-mono font-bold text-xs px-2.5 py-1 rounded-lg border-2 border-black">
              DOCS v2.0
            </span>
          </div>

          {/* Center Mode Switcher (Slide Mode vs Continuous Scroll) */}
          <div className="hidden lg:flex items-center bg-[#f4f4f0] p-1 rounded-xl border-2 border-black shadow-[2px_2px_0px_#000] gap-1">
            <button
              onClick={() => setViewMode("slide")}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono font-bold transition-all ${
                viewMode === "slide"
                  ? "bg-black text-[#ffe600] shadow-[1px_1px_0px_#000]"
                  : "text-gray-700 hover:text-black"
              }`}
            >
              <Sliders className="w-3.5 h-3.5" />
              <span>Slide Mode (Lean)</span>
            </button>
            <button
              onClick={() => setViewMode("continuous")}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono font-bold transition-all ${
                viewMode === "continuous"
                  ? "bg-black text-[#ffe600] shadow-[1px_1px_0px_#000]"
                  : "text-gray-700 hover:text-black"
              }`}
            >
              <ListFilter className="w-3.5 h-3.5" />
              <span>Continuous Scroll</span>
            </button>
          </div>

          <div className="flex items-center gap-2 sm:gap-3 font-mono text-xs font-bold">
            <Link
              to="/"
              className="bg-white hover:bg-gray-100 text-black px-3 py-1.5 rounded-xl border-2 border-black shadow-[2px_2px_0px_#000] transition active:translate-x-[1px] active:translate-y-[1px]"
            >
              Home
            </Link>
            <a
              href="https://github.com/SypherKx/InsightRAG"
              target="_blank"
              rel="noreferrer"
              className="bg-black hover:bg-gray-800 text-white px-3 py-1.5 rounded-xl border-2 border-black shadow-[2px_2px_0px_#000] transition active:translate-x-[1px] active:translate-y-[1px] flex items-center gap-1.5"
            >
              <Code className="w-3.5 h-3.5 text-[#ffe600]" />
              <span className="hidden sm:inline">GitHub</span>
            </a>
          </div>
        </div>
      </header>

      {/* Mobile Chapter Slider Bar */}
      <div className="md:hidden sticky top-[57px] z-40 bg-white/95 backdrop-blur-md border-b-2 border-black px-3 py-2 overflow-x-auto flex items-center gap-2 shadow-[0_2px_0px_#000]">
        <span className="font-mono text-[10px] font-bold text-gray-500 uppercase shrink-0">
          Ch. {activeChapterIndex + 1}/{chapters.length}
        </span>
        {chapters.map((ch, idx) => {
          const Icon = ch.icon;
          const isActive = activeChapterIndex === idx;
          return (
            <button
              key={ch.id}
              onClick={() => handleSelectChapter(idx)}
              className={`whitespace-nowrap px-3 py-1 rounded-lg border text-xs font-mono font-bold shrink-0 flex items-center gap-1.5 transition-all ${
                isActive
                  ? "bg-[#ffe600] text-black border-black shadow-[1.5px_1.5px_0px_#000]"
                  : "bg-gray-50 text-gray-700 border-gray-300"
              }`}
            >
              <Icon className="w-3 h-3" />
              <span>{ch.short}</span>
            </button>
          );
        })}
      </div>

      {/* Main Container */}
      <div className="max-w-7xl mx-auto px-4 sm:px-8 py-8 grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
        {/* Left Sticky Navigation Index */}
        <aside className="hidden md:block md:col-span-4 lg:col-span-3 md:sticky md:top-20 z-30 self-start">
          <div className="bg-white border-3 border-black rounded-2xl p-5 shadow-[5px_5px_0px_#000] space-y-5 max-h-[calc(100vh-6.5rem)] overflow-y-auto">
            {/* Header with progress */}
            <div className="flex items-center justify-between border-b-2 border-black pb-3">
              <div className="font-mono font-black text-xs uppercase tracking-wider text-black flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-[#ec4899]" />
                <span>Learning Index</span>
              </div>
              <span className="font-mono font-bold text-[11px] bg-[#ffe600] border border-black px-1.5 py-0.5 rounded">
                {activeChapterIndex + 1} / {chapters.length}
              </span>
            </div>

            {/* Category Groups */}
            {categories.map((category) => {
              const categoryChapters = chapters.filter((c) => c.category === category);
              return (
                <div key={category} className="space-y-1.5">
                  <div className="font-mono font-black text-[10px] text-gray-400 uppercase tracking-widest px-2">
                    {category}
                  </div>
                  <div className="space-y-1">
                    {categoryChapters.map((ch) => {
                      const idx = chapters.findIndex((c) => c.id === ch.id);
                      const isActive = activeChapterIndex === idx;
                      const Icon = ch.icon;

                      return (
                        <button
                          key={ch.id}
                          onClick={() => handleSelectChapter(idx)}
                          className={`w-full text-left flex items-center justify-between px-3 py-2 rounded-xl border-2 font-mono text-xs font-bold transition-all cursor-pointer ${
                            isActive
                              ? "bg-[#ffe600] text-black border-black shadow-[2px_2px_0px_#000] translate-x-1"
                              : "bg-transparent text-gray-700 border-transparent hover:border-black hover:bg-gray-50"
                          }`}
                        >
                          <div className="flex items-center gap-2 truncate">
                            <Icon className="w-3.5 h-3.5 shrink-0" />
                            <span className="truncate">{ch.short}</span>
                          </div>
                          {isActive && <ChevronRight className="w-3.5 h-3.5 shrink-0" />}
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}

            {/* View Mode Toggle in sidebar for mobile/tablet */}
            <div className="pt-2 border-t-2 border-black space-y-2">
              <button
                onClick={() => setViewMode(viewMode === "slide" ? "continuous" : "slide")}
                className="w-full flex items-center justify-between px-3 py-2 rounded-xl border-2 border-black bg-gray-50 hover:bg-gray-100 font-mono text-xs font-bold transition cursor-pointer"
              >
                <div className="flex items-center gap-2">
                  <Sliders className="w-3.5 h-3.5 text-black" />
                  <span>Mode:</span>
                </div>
                <span className="bg-black text-[#ffe600] px-2 py-0.5 rounded text-[10px]">
                  {viewMode === "slide" ? "Slide View" : "Continuous"}
                </span>
              </button>

              <a
                href="https://github.com/SypherKx/InsightRAG"
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-between px-3 py-2 rounded-xl border-2 border-black bg-black text-white hover:bg-gray-800 font-mono text-xs font-bold transition shadow-[2px_2px_0px_#000]"
              >
                <div className="flex items-center gap-2">
                  <Code className="w-3.5 h-3.5 text-[#ffe600]" />
                  <span>GitHub Source</span>
                </div>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>
        </aside>

        {/* Right Main Content Area */}
        <main className="col-span-1 md:col-span-8 lg:col-span-9 min-w-0">
          {viewMode === "slide" ? (
            /* ========================================================================= */
            /* SLIDE MODE: Focus on one clean chapter at a time with smooth transition   */
            /* ========================================================================= */
            <div className="space-y-6">
              {/* Slide Progress Topbar */}
              <div className="bg-white border-3 border-black rounded-2xl p-4 shadow-[4px_4px_0px_#000] flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-3">
                  <div className="bg-[#ffe600] text-black border-2 border-black rounded-xl p-2 font-mono font-black text-xs shadow-[1.5px_1.5px_0px_#000]">
                    #{activeChapterIndex + 1}
                  </div>
                  <div>
                    <div className="text-[11px] font-mono font-bold text-gray-500 uppercase tracking-wider">
                      {activeChapter.category}
                    </div>
                    <div className="text-base sm:text-lg font-black font-mono text-black">
                      {activeChapter.title}
                    </div>
                  </div>
                </div>

                {/* Next / Prev slide buttons */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={handlePrev}
                    disabled={activeChapterIndex === 0}
                    className="p-2 rounded-xl border-2 border-black bg-white hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed shadow-[2px_2px_0px_#000] active:scale-95 transition"
                    title="Previous Chapter (Left Arrow)"
                  >
                    <ArrowLeft className="w-4 h-4" />
                  </button>

                  <button
                    onClick={handleNext}
                    disabled={activeChapterIndex === chapters.length - 1}
                    className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl border-2 border-black bg-[#ffe600] hover:bg-yellow-400 font-mono font-bold text-xs shadow-[2px_2px_0px_#000] active:scale-95 transition disabled:opacity-30 disabled:cursor-not-allowed"
                    title="Next Chapter (Right Arrow)"
                  >
                    <span>Next</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Animated Slide Content */}
              <AnimatePresence mode="wait" custom={slideDirection}>
                <motion.div
                  key={activeChapter.id}
                  custom={slideDirection}
                  variants={slideVariants}
                  initial="enter"
                  animate="center"
                  exit="exit"
                  className="space-y-6"
                >
                  <ChapterContent
                    id={activeChapter.id}
                    copyToClipboard={copyToClipboard}
                    copiedCmd={copiedCmd}
                  />

                  {/* Bottom Navigation Buttons */}
                  <div className="bg-white border-3 border-black rounded-2xl p-5 shadow-[4px_4px_0px_#000] flex items-center justify-between flex-wrap gap-4">
                    {activeChapterIndex > 0 ? (
                      <button
                        onClick={handlePrev}
                        className="flex items-center gap-2 font-mono text-xs font-bold text-gray-700 hover:text-black border-2 border-black px-4 py-2 rounded-xl bg-white hover:bg-gray-50 shadow-[2px_2px_0px_#000] transition active:scale-95"
                      >
                        <ArrowLeft className="w-4 h-4" />
                        <span>Previous: {chapters[activeChapterIndex - 1].short}</span>
                      </button>
                    ) : (
                      <div />
                    )}

                    {activeChapterIndex < chapters.length - 1 ? (
                      <button
                        onClick={handleNext}
                        className="flex items-center gap-2 font-mono text-xs font-black text-black border-2 border-black px-4 py-2 rounded-xl bg-[#ffe600] hover:bg-yellow-400 shadow-[2px_2px_0px_#000] transition active:scale-95 ml-auto"
                      >
                        <span>Next: {chapters[activeChapterIndex + 1].short}</span>
                        <ArrowRight className="w-4 h-4" />
                      </button>
                    ) : (
                      <Link
                        to="/app/upload"
                        className="flex items-center gap-2 font-mono text-xs font-black text-white border-2 border-black px-5 py-2.5 rounded-xl bg-black hover:bg-gray-800 shadow-[2px_2px_0px_#000] transition active:scale-95 ml-auto"
                      >
                        <span>Launch Live Studio 🚀</span>
                      </Link>
                    )}
                  </div>
                </motion.div>
              </AnimatePresence>
            </div>
          ) : (
            /* ========================================================================= */
            /* CONTINUOUS SCROLL MODE: All chapters visible sequentially                 */
            /* ========================================================================= */
            <div className="space-y-12">
              {chapters.map((ch) => (
                <section key={ch.id} id={ch.id} className="scroll-mt-24 space-y-6">
                  <ChapterContent
                    id={ch.id}
                    copyToClipboard={copyToClipboard}
                    copiedCmd={copiedCmd}
                  />
                </section>
              ))}
            </div>
          )}

          {/* Bottom Footer */}
          <footer className="mt-12 border-3 border-black bg-white p-5 rounded-2xl shadow-[4px_4px_0px_#000] flex flex-col sm:flex-row items-center justify-between gap-4 font-mono text-xs text-gray-700">
            <div className="font-bold text-black flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              InsightRAG Universal Multimodal Knowledge Factory
            </div>
            <div>
              Crafted by <span className="font-bold text-black">Karan Pratap Singh</span>
            </div>
            <div className="text-gray-500">MIT License • 100% Local-First Privacy</div>
          </footer>
        </main>
      </div>
    </div>
  );
}

// =============================================================================
// RENDERERS FOR INDIVIDUAL CHAPTER CONTENTS (Lean, beginner-friendly & crisp)
// =============================================================================

function ChapterContent({
  id,
  copyToClipboard,
  copiedCmd,
}: {
  id: string;
  copyToClipboard: (text: string, id: string) => void;
  copiedCmd: string | null;
}) {
  switch (id) {
    // ---------------------------------------------------------------------------
    // 1. QUICKSTART & LAUNCH
    // ---------------------------------------------------------------------------
    case "quickstart":
      return (
        <div className="bg-white border-3 border-black rounded-2xl p-6 sm:p-8 shadow-[6px_6px_0px_#000] space-y-6">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="bg-[#ffe600] text-black font-mono font-black text-xs px-3 py-1 rounded-full border-2 border-black">
              CHAPTER 1
            </span>
            <span className="text-gray-400 font-mono text-xs font-bold">
              // 1-Line Universal Installer & Offline Launch
            </span>
          </div>

          <h2 className="text-2xl sm:text-3xl font-black font-mono tracking-tight">
            1-Line Setup & 1-Word Launch
          </h2>

          <p className="text-sm text-gray-800 leading-relaxed font-sans font-medium">
            InsightRAG is an autonomous, multimodal local-first RAG engine. It converts PDFs,
            technical manuals, textbooks, diagrams, and scans into an interactive AI studio on your
            PC with <strong>zero mandatory cloud bills</strong> and{" "}
            <strong>100% on-device vector privacy</strong>.
          </p>

          {/* 1-Line Installer Box */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-mono font-bold text-xs uppercase tracking-wider text-black flex items-center gap-1.5">
                <Terminal className="w-4 h-4 text-[#ec4899]" />
                Universal 1-Line Installer (Run from any folder)
              </span>
              <button
                onClick={() =>
                  copyToClipboard(`irm https://www.insightrag.tech/install.ps1 | iex`, "ps1")
                }
                className="flex items-center gap-1 bg-black text-white hover:bg-gray-800 text-[11px] font-mono font-bold px-2.5 py-1 rounded-lg border border-black cursor-pointer shadow-[1px_1px_0px_#000]"
              >
                {copiedCmd === "ps1" ? (
                  <Check className="w-3 h-3 text-[#ffe600]" />
                ) : (
                  <Copy className="w-3 h-3" />
                )}
                <span>{copiedCmd === "ps1" ? "Copied!" : "Copy"}</span>
              </button>
            </div>

            <div className="bg-black text-[#ffe600] font-mono text-xs sm:text-sm p-4 rounded-xl border-2 border-black shadow-[3px_3px_0px_#000] overflow-x-auto">
              <code># Paste into Windows PowerShell:</code>
              <br />
              <code className="text-white">irm https://www.insightrag.tech/install.ps1 | iex</code>
            </div>
          </div>

          {/* 100% Offline 1-Word Launch Card */}
          <div className="bg-emerald-50 border-3 border-black p-5 rounded-2xl shadow-[4px_4px_0px_#000] space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="bg-emerald-400 text-black font-mono font-black text-xs px-2.5 py-1 rounded-lg border-2 border-black shadow-[1px_1px_0px_#000]">
                  ⚡ SUBSEQUENT LAUNCHES
                </span>
                <span className="font-mono font-black text-xs sm:text-sm text-black">
                  1-Word Instant Offline Command
                </span>
              </div>
              <span className="text-[10px] font-mono font-bold text-emerald-900 bg-emerald-200 px-2 py-0.5 rounded border border-emerald-400">
                100% OFFLINE • NO INTERNET NEEDED
              </span>
            </div>

            <p className="text-xs sm:text-sm text-gray-800 font-medium leading-relaxed">
              Once installed, you never need the installer or internet connection again. Open any
              terminal and type:
            </p>

            <div className="flex items-center justify-between bg-black text-emerald-300 font-mono text-xs sm:text-sm font-bold px-4 py-3 rounded-xl border-2 border-black shadow-[2px_2px_0px_#000]">
              <div className="flex items-center gap-2">
                <span className="text-gray-500">PS&gt;</span>
                <span className="text-[#ffe600] text-sm sm:text-base">insightrag</span>
              </div>
              <button
                onClick={() => copyToClipboard("insightrag", "offline_cmd")}
                className="bg-[#ffe600] text-black text-[11px] px-3 py-1 rounded-lg border border-black hover:bg-yellow-400 font-black flex items-center gap-1 active:scale-95 transition"
              >
                {copiedCmd === "offline_cmd" ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                <span>{copiedCmd === "offline_cmd" ? "Copied!" : "Copy"}</span>
              </button>
            </div>

            <p className="text-[11px] text-emerald-900 font-mono font-bold flex items-center gap-1.5">
              <span>💡</span>
              <span>Automatically boots local AI backend pipelines and opens the Live Studio in your default browser.</span>
            </p>
          </div>

          {/* 3 Value Pillars */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
            <div className="bg-white border-2 border-black p-4 rounded-xl space-y-1.5 shadow-[2px_2px_0px_#000]">
              <div className="font-mono font-black text-xs flex items-center gap-1.5 text-black">
                <RefreshCw className="w-4 h-4 text-purple-600" />
                Zero-Conflict Updates
              </div>
              <p className="text-xs text-gray-600 leading-relaxed">
                Auto-updater fetches git improvements while strictly preserving your local SQLite database and uploads.
              </p>
            </div>

            <div className="bg-white border-2 border-black p-4 rounded-xl space-y-1.5 shadow-[2px_2px_0px_#000]">
              <div className="font-mono font-black text-xs flex items-center gap-1.5 text-black">
                <HardDrive className="w-4 h-4 text-blue-600" />
                Lightweight Weights
              </div>
              <p className="text-xs text-gray-600 leading-relaxed">
                Pulls compact on-device sentence transformers once (80MB) and stores them permanently in local cache.
              </p>
            </div>

            <div className="bg-white border-2 border-black p-4 rounded-xl space-y-1.5 shadow-[2px_2px_0px_#000]">
              <div className="font-mono font-black text-xs flex items-center gap-1.5 text-black">
                <Zap className="w-4 h-4 text-amber-500" />
                1-Click Desktop
              </div>
              <p className="text-xs text-gray-600 leading-relaxed">
                Prefer double-clicking? Just double-click <code className="bg-gray-100 px-1 rounded font-bold">run.bat</code> in the cloned repository folder.
              </p>
            </div>
          </div>
        </div>
      );

    // ---------------------------------------------------------------------------
    // 2. DEEP INGESTION & VISUAL ROI
    // ---------------------------------------------------------------------------
    case "ingestion":
      return (
        <div className="bg-white border-3 border-black rounded-2xl p-6 sm:p-8 shadow-[6px_6px_0px_#000] space-y-6">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="bg-[#ec4899] text-white font-mono font-black text-xs px-3 py-1 rounded-full border-2 border-black">
              CHAPTER 2
            </span>
            <span className="text-gray-400 font-mono text-xs font-bold">
              // High-Fidelity Page Parsing & Diagram Auto-Cropping
            </span>
          </div>

          <h2 className="text-2xl sm:text-3xl font-black font-mono tracking-tight">
            Deep Page-by-Page Ingestion & Visual ROI
          </h2>

          <p className="text-sm text-gray-800 leading-relaxed font-sans font-medium">
            Conventional RAG tools strip PDFs down to plain text, completely throwing away diagrams,
            flowcharts, math equations, and circuit schematics. InsightRAG inspects every single page
            with an object-level layout detector.
          </p>

          {/* 3 Clean Ingestion Pillars */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-pink-50/50 border-2 border-black p-4 rounded-xl space-y-2 shadow-[3px_3px_0px_#000]">
              <div className="font-mono font-black text-xs flex items-center gap-1.5 text-black">
                <Layers className="w-4 h-4 text-[#ec4899]" />
                30px Vector Drawing Detection
              </div>
              <p className="text-xs text-gray-700 leading-relaxed">
                Inspects native PDF vector paths (<code className="font-bold">fitz.get_drawings()</code>). Any drawing larger than 30px is recognized as a technical illustration or graph.
              </p>
            </div>

            <div className="bg-blue-50/50 border-2 border-black p-4 rounded-xl space-y-2 shadow-[3px_3px_0px_#000]">
              <div className="font-mono font-black text-xs flex items-center gap-1.5 text-black">
                <Eye className="w-4 h-4 text-blue-600" />
                80-Char Fallback to 200 DPI OCR
              </div>
              <p className="text-xs text-gray-700 leading-relaxed">
                If a page yields under 80 text characters (e.g. scanned contracts or dirty images), it automatically triggers a sharp 200 DPI OCR render to capture every word.
              </p>
            </div>

            <div className="bg-purple-50/50 border-2 border-black p-4 rounded-xl space-y-2 shadow-[3px_3px_0px_#000]">
              <div className="font-mono font-black text-xs flex items-center gap-1.5 text-black">
                <Sparkles className="w-4 h-4 text-purple-600" />
                Targeted Diagram Auto-Cropping
              </div>
              <p className="text-xs text-gray-700 leading-relaxed">
                When you ask about a specific chart, the engine crops only that exact bounding box with clean padding and embeds a high-res interactive preview in chat.
              </p>
            </div>
          </div>

          {/* How Visual Evidence Card works */}
          <div className="bg-gray-50 border-2 border-black p-5 rounded-xl space-y-3 shadow-[3px_3px_0px_#000]">
            <div className="flex items-center gap-2 font-mono font-black text-xs text-black">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>📷 Visual Evidence in Answers (Click to Zoom)</span>
            </div>
            <p className="text-xs text-gray-700 leading-relaxed">
              Whenever the AI answers a technical query referencing a diagram (e.g., <em>"Transformer Attention Architecture"</em> or <em>"Figure 4 Block Diagram"</em>), a high-resolution visual evidence badge appears below the answer. Clicking the card opens a full-screen zoomable lightbox with exact page citation metadata.
            </p>
          </div>
        </div>
      );

    // ---------------------------------------------------------------------------
    // 3. FULLSCREEN STUDIO & CONVERSATIONAL MEMORY
    // ---------------------------------------------------------------------------
    case "studio":
      return (
        <div className="bg-white border-3 border-black rounded-2xl p-6 sm:p-8 shadow-[6px_6px_0px_#000] space-y-6">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="bg-purple-600 text-white font-mono font-black text-xs px-3 py-1 rounded-full border-2 border-black">
              CHAPTER 3
            </span>
            <span className="text-gray-400 font-mono text-xs font-bold">
              // Two-Phase Workflow & Conversational Context
            </span>
          </div>

          <h2 className="text-2xl sm:text-3xl font-black font-mono tracking-tight">
            Fullscreen Chat Studio & Multi-Turn Memory
          </h2>

          <p className="text-sm text-gray-800 leading-relaxed font-sans font-medium">
            InsightRAG splits knowledge generation into two distinct, distraction-free phases: thorough
            background ingestion and a dedicated, full-screen conversation workspace.
          </p>

          {/* Ingestion Gating Flow */}
          <div className="bg-white border-2 border-black p-4 rounded-xl shadow-[3px_3px_0px_#000] space-y-3">
            <div className="font-mono font-black text-xs text-black uppercase tracking-wider">
              1. Two-Phase Ingestion Gating
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 font-mono text-xs">
              <div className="bg-gray-100 p-2.5 rounded-lg border border-gray-300">
                <span className="text-gray-500 font-bold">STAGE 1</span>
                <div className="font-bold text-black mt-1">Reading Pages</div>
              </div>
              <div className="bg-gray-100 p-2.5 rounded-lg border border-gray-300">
                <span className="text-gray-500 font-bold">STAGE 2</span>
                <div className="font-bold text-black mt-1">Extracting Graphics</div>
              </div>
              <div className="bg-gray-100 p-2.5 rounded-lg border border-gray-300">
                <span className="text-gray-500 font-bold">STAGE 3</span>
                <div className="font-bold text-black mt-1">Vectorizing Chunks</div>
              </div>
              <div className="bg-[#ffe600] p-2.5 rounded-lg border border-black text-black">
                <span className="text-black font-black">STAGE 4</span>
                <div className="font-black mt-1">Studio Unlocked 🚀</div>
              </div>
            </div>
            <p className="text-xs text-gray-600 leading-relaxed font-sans">
              No partial or broken query states: chat unlocks only after document parsing, OCR, and vector indices are 100% verified.
            </p>
          </div>

          {/* ChatGPT-style Memory & Controls */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-purple-50 border-2 border-black p-4 rounded-xl space-y-2 shadow-[3px_3px_0px_#000]">
              <div className="font-mono font-black text-xs flex items-center gap-1.5 text-black">
                <MessageSquare className="w-4 h-4 text-purple-600" />
                Multi-Turn Contextual Memory
              </div>
              <p className="text-xs text-gray-700 leading-relaxed">
                Ask follow-up questions naturally like <em>"Why did the author suggest this in step 2?"</em>. The engine retains conversational context and cites previous answers seamlessly.
              </p>
            </div>

            <div className="bg-emerald-50 border-2 border-black p-4 rounded-xl space-y-2 shadow-[3px_3px_0px_#000]">
              <div className="font-mono font-black text-xs flex items-center gap-1.5 text-black">
                <HardDrive className="w-4 h-4 text-emerald-600" />
                LocalStorage Persistence & Back Nav
              </div>
              <p className="text-xs text-gray-700 leading-relaxed">
                Chats auto-save instantly to your browser storage. Accidental refreshes never erase your questions or diagrams. Use <strong>"← Back to Documents"</strong> anytime to add more files.
              </p>
            </div>
          </div>
        </div>
      );

    // ---------------------------------------------------------------------------
    // 4. SELECTIVE PAGE RANGE SLICING
    // ---------------------------------------------------------------------------
    case "slicing":
      return (
        <div className="bg-white border-3 border-black rounded-2xl p-6 sm:p-8 shadow-[6px_6px_0px_#000] space-y-6">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="bg-blue-600 text-white font-mono font-black text-xs px-3 py-1 rounded-full border-2 border-black">
              CHAPTER 4
            </span>
            <span className="text-gray-400 font-mono text-xs font-bold">
              // Target Specific Chapters from Massive Books
            </span>
          </div>

          <h2 className="text-2xl sm:text-3xl font-black font-mono tracking-tight">
            Selective Page Range Slicing
          </h2>

          <p className="text-sm text-gray-800 leading-relaxed font-sans font-medium">
            Have a 1,200-page textbook or a 600-page enterprise specification manual? You rarely need
            to index the entire document when you only care about one chapter or syllabus module.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white border-2 border-black p-5 rounded-xl space-y-3 shadow-[3px_3px_0px_#000]">
              <div className="font-mono font-black text-xs text-black uppercase flex items-center gap-1.5">
                <Scissors className="w-4 h-4 text-blue-600" />
                How It Works in Studio
              </div>
              <p className="text-xs text-gray-700 leading-relaxed">
                In the upload interface, toggle <strong>"Selective Page Range"</strong> and specify:
              </p>
              <div className="bg-gray-100 p-3 rounded-lg border border-gray-300 font-mono text-xs space-y-1">
                <div>Start Page: <span className="font-bold text-black">45</span></div>
                <div>End Page: <span className="font-bold text-black">80</span></div>
              </div>
              <p className="text-xs text-gray-600">
                Only pages 45 through 80 are extracted, OCR-parsed, and embedded into FAISS.
              </p>
            </div>

            <div className="bg-amber-50 border-2 border-black p-5 rounded-xl space-y-3 shadow-[3px_3px_0px_#000]">
              <div className="font-mono font-black text-xs text-black uppercase flex items-center gap-1.5">
                <Zap className="w-4 h-4 text-amber-600" />
                Key Benefits
              </div>
              <ul className="text-xs text-gray-700 space-y-2">
                <li className="flex items-start gap-2">
                  <Check className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
                  <span><strong>10x Faster Ingestion:</strong> Processes in 5 seconds instead of 2 minutes.</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
                  <span><strong>Zero Memory Bloat:</strong> Keeps RAM footprint minimal even on lightweight laptops.</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
                  <span><strong>Higher Precision:</strong> Irrelevant chapters never pollute the vector retrieval rank.</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      );

    // ---------------------------------------------------------------------------
    // 5. DUAL COMPUTE & SPEED-TIERED EMBEDDINGS
    // ---------------------------------------------------------------------------
    case "compute":
      return (
        <div className="bg-white border-3 border-black rounded-2xl p-6 sm:p-8 shadow-[6px_6px_0px_#000] space-y-6">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="bg-emerald-600 text-white font-mono font-black text-xs px-3 py-1 rounded-full border-2 border-black">
              CHAPTER 5
            </span>
            <span className="text-gray-400 font-mono text-xs font-bold">
              // Local Air-Gapped vs Turbo Cloud & Embedding Models
            </span>
          </div>

          <h2 className="text-2xl sm:text-3xl font-black font-mono tracking-tight">
            Dual Compute Architecture & Speed-Tiered Embeddings
          </h2>

          <p className="text-sm text-gray-800 leading-relaxed font-sans font-medium">
            InsightRAG offers complete architectural flexibility: run entirely offline on your PC's
            hardware, or connect cloud API keys whenever you want 100-token/sec turbo speeds.
          </p>

          {/* Dual Compute Side-by-Side */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-emerald-50 border-2 border-black p-5 rounded-xl space-y-2 shadow-[3px_3px_0px_#000]">
              <span className="bg-emerald-600 text-white font-mono font-bold text-[10px] px-2 py-0.5 rounded">
                DEFAULT MODE
              </span>
              <div className="font-mono font-black text-base text-black">💻 100% Local Air-Gapped</div>
              <p className="text-xs text-gray-700 leading-relaxed">
                Powered by <strong>Ollama</strong> (<code className="font-bold">llama3.2:3b</code>, <code className="font-bold">qwen2.5</code>) and local CPU FAISS vector storage. Zero network calls, zero telemetry, full privacy.
              </p>
            </div>

            <div className="bg-[#ffe600]/20 border-2 border-black p-5 rounded-xl space-y-2 shadow-[3px_3px_0px_#000]">
              <span className="bg-black text-[#ffe600] font-mono font-bold text-[10px] px-2 py-0.5 rounded">
                OPTIONAL BYOK
              </span>
              <div className="font-mono font-black text-base text-black">⚡ Advance Turbo Server</div>
              <p className="text-xs text-gray-700 leading-relaxed">
                Plug in your own API key for <strong>Groq Llama 3.3 70B</strong> (ultra-low latency), <strong>Google Gemini 1.5 Flash</strong>, or <strong>OpenAI GPT-4o-mini</strong>.
              </p>
            </div>
          </div>

          {/* Speed-Tiered Embeddings */}
          <div className="space-y-3 pt-2">
            <div className="font-mono font-black text-xs text-black uppercase tracking-wider">
              Speed-Tiered Dense Embeddings
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 font-mono text-xs">
              <div className="bg-white border-2 border-black p-3.5 rounded-xl shadow-[2px_2px_0px_#000] space-y-1">
                <span className="bg-emerald-100 text-emerald-800 font-bold px-1.5 py-0.5 rounded text-[10px]">
                  5x ULTRA FAST
                </span>
                <div className="font-black text-black">all-MiniLM-L6-v2</div>
                <p className="text-gray-600 text-[11px] font-sans">
                  384 dimensions. Extremely CPU-friendly. Perfect for laptops and fast previews.
                </p>
              </div>

              <div className="bg-white border-2 border-black p-3.5 rounded-xl shadow-[2px_2px_0px_#000] space-y-1">
                <span className="bg-blue-100 text-blue-800 font-bold px-1.5 py-0.5 rounded text-[10px]">
                  3x BALANCED
                </span>
                <div className="font-black text-black">bge-small-en-v1.5</div>
                <p className="text-gray-600 text-[11px] font-sans">
                  384 dimensions. High retrieval accuracy for general technical documents.
                </p>
              </div>

              <div className="bg-white border-2 border-black p-3.5 rounded-xl shadow-[2px_2px_0px_#000] space-y-1">
                <span className="bg-purple-100 text-purple-800 font-bold px-1.5 py-0.5 rounded text-[10px]">
                  HIGH PRECISION
                </span>
                <div className="font-black text-black">bge-base-en-v1.5</div>
                <p className="text-gray-600 text-[11px] font-sans">
                  768 dimensions. Deep semantic nuance for complex research & medical papers.
                </p>
              </div>

              <div className="bg-white border-2 border-black p-3.5 rounded-xl shadow-[2px_2px_0px_#000] space-y-1">
                <span className="bg-amber-100 text-amber-800 font-bold px-1.5 py-0.5 rounded text-[10px]">
                  8K TOKEN WINDOW
                </span>
                <div className="font-black text-black">nomic-embed-text</div>
                <p className="text-gray-600 text-[11px] font-sans">
                  768 dimensions. Native Ollama embedding with massive 8,192 token context.
                </p>
              </div>
            </div>
          </div>
        </div>
      );

    // ---------------------------------------------------------------------------
    // 6. ENTERPRISE HARDENING & PRIVACY
    // ---------------------------------------------------------------------------
    case "security":
      return (
        <div className="bg-white border-3 border-black rounded-2xl p-6 sm:p-8 shadow-[6px_6px_0px_#000] space-y-6">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="bg-amber-500 text-black font-mono font-black text-xs px-3 py-1 rounded-full border-2 border-black">
              CHAPTER 6
            </span>
            <span className="text-gray-400 font-mono text-xs font-bold">
              // OWASP Protection, Path Sanitization & Anti-Hallucination
            </span>
          </div>

          <h2 className="text-2xl sm:text-3xl font-black font-mono tracking-tight">
            Enterprise Security & Guardrails
          </h2>

          <p className="text-sm text-gray-800 leading-relaxed font-sans font-medium">
            InsightRAG is audited against standard web and generative AI vulnerability vectors.
            Your files and system remain protected from malicious inputs.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
            <div className="bg-white border-2 border-black p-4 rounded-xl space-y-2 shadow-[2px_2px_0px_#000]">
              <div className="font-black text-sm text-black flex items-center gap-1.5">
                <Lock className="w-4 h-4 text-emerald-600" />
                OWASP Security Headers
              </div>
              <p className="text-gray-600 leading-relaxed font-sans">
                Appends <code className="font-bold">X-Frame-Options: DENY</code>, <code className="font-bold">X-Content-Type-Options: nosniff</code>, and strict Content Security Policies across all responses.
              </p>
            </div>

            <div className="bg-white border-2 border-black p-4 rounded-xl space-y-2 shadow-[2px_2px_0px_#000]">
              <div className="font-black text-sm text-black flex items-center gap-1.5">
                <Shield className="w-4 h-4 text-blue-600" />
                Path Traversal & LFI Defense
              </div>
              <p className="text-gray-600 leading-relaxed font-sans">
                Incoming filenames are sanitized via <code className="font-bold">sanitize_filename</code> to neutralize <code className="font-bold">../</code> directory escapes and protect system drives.
              </p>
            </div>

            <div className="bg-white border-2 border-black p-4 rounded-xl space-y-2 shadow-[2px_2px_0px_#000]">
              <div className="font-black text-sm text-black flex items-center gap-1.5">
                <HardDrive className="w-4 h-4 text-purple-600" />
                Decompression Bomb Protection
              </div>
              <p className="text-gray-600 leading-relaxed font-sans">
                Caps image allocations at 25,000,000 pixels (<code className="font-bold">Image.MAX_IMAGE_PIXELS</code>) and limits docx uncompressed XML sizes to prevent memory-flooding DoS.
              </p>
            </div>

            <div className="bg-white border-2 border-black p-4 rounded-xl space-y-2 shadow-[2px_2px_0px_#000]">
              <div className="font-black text-sm text-black flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-pink-600" />
                Prompt Injection Sandboxing
              </div>
              <p className="text-gray-600 leading-relaxed font-sans">
                RAG contexts are encapsulated within strict <code className="font-bold">&lt;document_context&gt;</code> isolation delimiters to prevent prompt override attacks.
              </p>
            </div>
          </div>
        </div>
      );

    // ---------------------------------------------------------------------------
    // 7. STANDALONE TURNKEY EXPORT
    // ---------------------------------------------------------------------------
    case "standalone":
      return (
        <div className="bg-white border-3 border-black rounded-2xl p-6 sm:p-8 shadow-[6px_6px_0px_#000] space-y-6">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="bg-cyan-600 text-white font-mono font-black text-xs px-3 py-1 rounded-full border-2 border-black">
              CHAPTER 7
            </span>
            <span className="text-gray-400 font-mono text-xs font-bold">
              // 1-Click Portable Offline Bundle
            </span>
          </div>

          <h2 className="text-2xl sm:text-3xl font-black font-mono tracking-tight">
            Turnkey Standalone ZIP Export
          </h2>

          <p className="text-sm text-gray-800 leading-relaxed font-sans font-medium">
            Once your documents are indexed, export a completely self-contained ZIP bundle that
            runs offline on any PC with zero external dependency setup.
          </p>

          {/* Export Bundle Contents */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono text-xs">
            <div className="bg-white border-2 border-black p-3.5 rounded-xl shadow-[2px_2px_0px_#000] space-y-1">
              <span className="font-black text-black text-sm">📁 vector_db/</span>
              <p className="text-gray-600 text-[11px] font-sans">
                Pre-indexed FAISS / ChromaDB vector database with all document embeddings.
              </p>
            </div>

            <div className="bg-white border-2 border-black p-3.5 rounded-xl shadow-[2px_2px_0px_#000] space-y-1">
              <span className="font-black text-black text-sm">📁 images/</span>
              <p className="text-gray-600 text-[11px] font-sans">
                Extracted high-resolution diagram crops and figures ready for visual search.
              </p>
            </div>

            <div className="bg-white border-2 border-black p-3.5 rounded-xl shadow-[2px_2px_0px_#000] space-y-1">
              <span className="font-black text-black text-sm">⚡ run.bat & run.sh</span>
              <p className="text-gray-600 text-[11px] font-sans">
                1-click native launchers that boot the lightweight server in under 0.1 seconds.
              </p>
            </div>

            <div className="bg-white border-2 border-black p-3.5 rounded-xl shadow-[2px_2px_0px_#000] space-y-1">
              <span className="font-black text-black text-sm">🌐 server.py & index.html</span>
              <p className="text-gray-600 text-[11px] font-sans">
                Ultra-fast FastAPI microservice with persistent LocalStorage auto-save.
              </p>
            </div>
          </div>

          <div className="bg-black text-[#ffe600] font-mono text-xs p-4 rounded-xl border-2 border-black shadow-[3px_3px_0px_#000] space-y-1">
            <div className="text-gray-400"># Run the exported bundle on Windows:</div>
            <div className="text-white font-bold">.\run.bat</div>
            <div className="text-gray-400 pt-1.5"># Run on macOS or Linux:</div>
            <div className="text-white font-bold">chmod +x run.sh && ./run.sh</div>
          </div>
        </div>
      );

    // ---------------------------------------------------------------------------
    // 8. REST API REFERENCE
    // ---------------------------------------------------------------------------
    case "api":
      return (
        <div className="bg-white border-3 border-black rounded-2xl p-6 sm:p-8 shadow-[6px_6px_0px_#000] space-y-6">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="bg-indigo-600 text-white font-mono font-black text-xs px-3 py-1 rounded-full border-2 border-black">
              CHAPTER 8
            </span>
            <span className="text-gray-400 font-mono text-xs font-bold">
              // HTTP REST API Reference
            </span>
          </div>

          <h2 className="text-2xl sm:text-3xl font-black font-mono tracking-tight">
            Developer REST API
          </h2>

          <p className="text-sm text-gray-800 leading-relaxed font-sans font-medium">
            Integrate InsightRAG directly into your custom web apps, internal dashboards, or Discord
            bots via standard HTTP REST endpoints.
          </p>

          {/* Clean API Table */}
          <div className="border-2 border-black rounded-xl overflow-hidden shadow-[3px_3px_0px_#000]">
            <div className="overflow-x-auto">
              <table className="w-full text-left font-mono text-xs">
                <thead className="bg-black text-white uppercase text-[11px] font-bold">
                  <tr>
                    <th className="p-3 border-r border-gray-700 w-24">Method</th>
                    <th className="p-3 border-r border-gray-700">Endpoint</th>
                    <th className="p-3">Purpose</th>
                  </tr>
                </thead>
                <tbody className="divide-y-2 divide-black bg-white font-medium">
                  <tr>
                    <td className="p-3 border-r-2 border-black">
                      <span className="bg-emerald-100 text-emerald-800 font-black px-2 py-0.5 rounded border border-emerald-800">
                        POST
                      </span>
                    </td>
                    <td className="p-3 border-r-2 border-black font-bold">/api/sessions/create</td>
                    <td className="p-3 text-gray-700 font-sans">
                      Creates an isolated RAG session with private vector storage.
                    </td>
                  </tr>
                  <tr>
                    <td className="p-3 border-r-2 border-black">
                      <span className="bg-emerald-100 text-emerald-800 font-black px-2 py-0.5 rounded border border-emerald-800">
                        POST
                      </span>
                    </td>
                    <td className="p-3 border-r-2 border-black font-bold">
                      /api/sessions/&#123;id&#125;/upload
                    </td>
                    <td className="p-3 text-gray-700 font-sans">
                      Uploads and parses a PDF, Word document, or image with page range options.
                    </td>
                  </tr>
                  <tr>
                    <td className="p-3 border-r-2 border-black">
                      <span className="bg-emerald-100 text-emerald-800 font-black px-2 py-0.5 rounded border border-emerald-800">
                        POST
                      </span>
                    </td>
                    <td className="p-3 border-r-2 border-black font-bold">
                      /api/sessions/&#123;id&#125;/chat
                    </td>
                    <td className="p-3 text-gray-700 font-sans">
                      Submits a query with multi-turn conversational context and visual diagram evidence.
                    </td>
                  </tr>
                  <tr>
                    <td className="p-3 border-r-2 border-black">
                      <span className="bg-blue-100 text-blue-800 font-black px-2 py-0.5 rounded border border-blue-800">
                        GET
                      </span>
                    </td>
                    <td className="p-3 border-r-2 border-black font-bold">
                      /api/sessions/&#123;id&#125;/export
                    </td>
                    <td className="p-3 text-gray-700 font-sans">
                      Downloads the turnkey standalone ZIP package.
                    </td>
                  </tr>
                  <tr>
                    <td className="p-3 border-r-2 border-black">
                      <span className="bg-gray-100 text-gray-800 font-black px-2 py-0.5 rounded border border-gray-800">
                        GET
                      </span>
                    </td>
                    <td className="p-3 border-r-2 border-black font-bold">/api/health</td>
                    <td className="p-3 text-gray-700 font-sans">
                      Returns Ollama connectivity, active GPU/CPU, and vector index health.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      );

    default:
      return null;
  }
}

