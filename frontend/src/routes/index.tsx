import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { motion } from "framer-motion";
import {
  Copy,
  Check,
  ArrowRight,
  Terminal,
  Cpu,
  Shield,
  Layers,
  Sparkles,
  ExternalLink,
  BookOpen,
  Code,
} from "lucide-react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "InsightRAG" },
      {
        name: "description",
        content:
          "Turn any documents, PDFs, diagrams, and images into a turnkey, anti-hallucination local AI knowledge studio with 100% on-device privacy.",
      },
    ],
  }),
  component: LandingPage,
});

export function LandingPage() {
  const [copied, setCopied] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const cliCommand = `irm https://raw.githubusercontent.com/SypherKx/InsightRAG/main/install.ps1 | iex`;

  const handleCopyCLI = () => {
    navigator.clipboard.writeText(cliCommand);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-black text-white font-sans selection:bg-[#ffe600] selection:text-black overflow-x-hidden">
      {/* 
        ========================================================================
        HERO SECTION (Sky Noise Textured Background - Responsive Neo-Brutalist)
        ========================================================================
      */}
      <div
        className="relative bg-cover bg-center bg-no-repeat border-b-4 border-black min-h-[92vh] flex flex-col justify-between"
        style={{
          backgroundImage: `url('/assets/skytextured.jpg'), url('/skytextured.jpg')`,
          backgroundColor: "#86b0d9",
        }}
      >
        {/* Top Navbar */}
        <header className="p-3 sm:p-5 md:p-6 max-w-7xl mx-auto w-full z-30">
          <div className="flex items-center justify-between gap-2 sm:gap-4">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2 group">
              <span className="bg-black text-white font-black font-mono text-base sm:text-lg md:text-xl px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-xl border-2 border-black shadow-[2px_2px_0px_#000] sm:shadow-[3px_3px_0px_#000] italic tracking-tighter group-hover:bg-[#ffe600] group-hover:text-black transition-colors">
                InsightRAG
              </span>
            </Link>

            {/* Desktop / Tablet Navigation Pill */}
            <nav className="hidden sm:flex items-center gap-3 md:gap-6 bg-white/95 backdrop-blur-md px-4 md:px-6 py-1.5 md:py-2 rounded-full border-2 border-black shadow-[2px_2px_0px_#000] sm:shadow-[3px_3px_0px_#000] font-mono text-[11px] md:text-xs font-bold text-black">
              <a href="#capabilities" className="hover:underline text-black">
                Capabilities
              </a>
              <a href="#about" className="hover:underline text-black">
                About
              </a>
              <Link to="/docs" className="hover:underline text-black font-black">
                Docs
              </Link>
              <a
                href="https://github.com/SypherKx/InsightRAG"
                target="_blank"
                rel="noreferrer"
                className="hover:underline flex items-center gap-1 text-black"
              >
                <Code className="w-3.5 h-3.5" />
                <span>GitHub</span>
              </a>
            </nav>

            {/* Top Right Action Button */}
            <div className="flex items-center gap-2">
              <button
                onClick={handleCopyCLI}
                className="bg-[#ffe600] text-black hover:bg-yellow-400 font-mono font-black text-[11px] sm:text-xs px-3 sm:px-4 py-1.5 sm:py-2.5 rounded-lg sm:rounded-xl border-2 border-black shadow-[2px_2px_0px_#000] sm:shadow-[3px_3px_0px_#000] flex items-center gap-1.5 cursor-pointer transition-all active:translate-x-[1px] active:translate-y-[1px] shrink-0"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-black" /> : <Copy className="w-3.5 h-3.5 text-black" />}
                <span className="hidden xs:inline">{copied ? "COPIED 1-LINER!" : "COPY 1-LINER"}</span>
                <span className="xs:hidden">{copied ? "✓" : "COPY"}</span>
              </button>
            </div>
          </div>

          {/* Mobile Quick Links Bar (< sm) */}
          <div className="sm:hidden mt-2 flex items-center justify-center gap-2 bg-white/95 backdrop-blur-md px-3 py-1 rounded-lg border border-black text-[11px] font-mono font-bold text-black shadow-[1px_1px_0px_#000]">
            <Link to="/docs" className="px-2 py-0.5 hover:underline font-black">
              📖 Docs
            </Link>
            <span className="text-gray-300">|</span>
            <a href="#capabilities" className="px-2 py-0.5 hover:underline">
              ⚡ Features
            </a>
            <span className="text-gray-300">|</span>
            <a
              href="https://github.com/SypherKx/InsightRAG"
              target="_blank"
              rel="noreferrer"
              className="px-2 py-0.5 hover:underline"
            >
              💻 GitHub
            </a>
          </div>
        </header>

        {/* Hero Central Content */}
        <main className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10 md:py-12 text-center space-y-4 sm:space-y-6 z-10 my-auto w-full">
          {/* Eyebrow Badge */}
          <div className="inline-block bg-black text-[#ffe600] font-mono font-black text-[10px] sm:text-xs px-3 sm:px-4 py-1 sm:py-1.5 rounded-full border-2 border-black shadow-[2px_2px_0px_#000] sm:shadow-[3px_3px_0px_#000] uppercase tracking-wider max-w-full">
            UNIVERSAL MULTIMODAL RAG & INTELLIGENCE FACTORY
          </div>

          {/* Display Headline */}
          <h1 className="text-3xl xs:text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-black font-sans text-black tracking-tight leading-[1.08] sm:leading-[1.05] drop-shadow-[0_2px_0_rgba(255,255,255,0.8)] sm:drop-shadow-[0_4px_0_rgba(255,255,255,0.8)] px-1">
            Autonomous Multimodal <br className="hidden xs:inline" />
            <span className="bg-[#ffe600] text-black px-2 py-0.5 rounded border-2 border-black inline-block shadow-[3px_3px_0px_#000] sm:shadow-[4px_4px_0px_#000] mt-1 text-2xl xs:text-3xl sm:text-5xl md:text-6xl lg:text-7xl">
              RAG-in-a-Box Factory
            </span>
          </h1>

          {/* Subtitle */}
          <p className="max-w-2xl mx-auto text-black font-mono font-bold text-xs sm:text-sm md:text-base leading-relaxed bg-white/80 backdrop-blur-sm p-3 sm:p-4 rounded-xl border-2 border-black shadow-[2px_2px_0px_#000] sm:shadow-[3px_3px_0px_#000]">
            Turn complex manuals, technical blueprints, research papers, diagrams, books, and enterprise
            documents into a turnkey, anti-hallucination AI knowledge studio in seconds.
          </p>

          {/* Interactive Command Box with Multi-Platform Tabs */}
          <div className="max-w-2xl mx-auto bg-black text-white p-3 sm:p-4 rounded-2xl border-2 border-black shadow-[4px_4px_0px_#000] sm:shadow-[6px_6px_0px_#000] space-y-2.5 font-mono text-xs sm:text-sm text-left">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-800 pb-2">
              <div className="flex items-center gap-1.5 text-[10px] sm:text-xs">
                <span className="text-[#ffe600] font-black">⚡ 1-LINE INSTALL</span>
                <span className="text-gray-500">|</span>
                <span className="text-emerald-400 font-bold">100% Local Air-Gapped</span>
              </div>
              <span className="text-[9px] bg-[#1a1a1a] text-gray-300 px-2 py-0.5 rounded border border-gray-700">
                Zero Setup Bills
              </span>
            </div>

            <div className="flex items-center gap-2 justify-between bg-[#0d1117] rounded-xl p-2 sm:px-3 sm:py-2.5 border border-gray-800">
              <div className="flex items-center gap-1.5 sm:gap-2 overflow-x-auto text-emerald-400 font-bold flex-1 min-w-0 scrollbar-none">
                <span className="text-gray-500 flex-shrink-0 text-xs font-mono">PS&gt;</span>
                <code className="whitespace-nowrap text-[10px] sm:text-xs text-emerald-300">
                  {cliCommand}
                </code>
              </div>
              <button
                onClick={handleCopyCLI}
                className="bg-[#ffe600] text-black font-black font-mono text-[10px] sm:text-xs px-2.5 sm:px-3.5 py-1.5 rounded-lg border-2 border-black hover:bg-yellow-400 cursor-pointer flex-shrink-0 flex items-center gap-1 ml-1 sm:ml-2 active:scale-95 transition"
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? "COPIED!" : "COPY"}</span>
              </button>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] text-gray-400 font-mono pt-0.5">
              <span>💡 Or double-click <strong className="text-white">run.bat</strong> in folder</span>
              <span className="text-gray-500">Auto-launches browser on completion</span>
            </div>
          </div>

          {/* Action Buttons (Mobile stacked, tablet/desktop row) */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-center gap-3 sm:gap-4 pt-1 sm:pt-2 max-w-md sm:max-w-none mx-auto">
            <button
              onClick={handleCopyCLI}
              className="w-full sm:w-auto bg-[#ffe600] text-black hover:bg-yellow-400 font-black font-mono text-xs sm:text-sm px-5 sm:px-6 py-3 sm:py-3.5 rounded-xl border-3 border-black shadow-[3px_3px_0px_#000] sm:shadow-[4px_4px_0px_#000] flex items-center justify-center gap-2 cursor-pointer transition-all active:translate-x-[2px] active:translate-y-[2px]"
            >
              {copied ? <Check className="w-4 h-4 sm:w-5 sm:h-5 text-black" /> : <Terminal className="w-4 h-4 sm:w-5 sm:h-5 text-black" />}
              <span>{copied ? "COPIED 1-LINE COMMAND!" : "⚡ COPY 1-LINE LAUNCHER"}</span>
            </button>

            <Link to="/docs" className="w-full sm:w-auto">
              <button className="w-full sm:w-auto bg-white text-black hover:bg-gray-100 font-black font-mono text-xs sm:text-sm px-5 sm:px-6 py-3 sm:py-3.5 rounded-xl border-3 border-black shadow-[3px_3px_0px_#000] sm:shadow-[4px_4px_0px_#000] flex items-center justify-center gap-2 cursor-pointer transition-all active:translate-x-[2px] active:translate-y-[2px]">
                <BookOpen className="w-4 h-4 sm:w-5 sm:h-5 text-black" />
                <span>EXPLORE DOCS</span>
              </button>
            </Link>

            <a
              href="https://github.com/SypherKx/InsightRAG"
              target="_blank"
              rel="noreferrer"
              className="w-full sm:w-auto"
            >
              <button className="w-full sm:w-auto bg-[#0d1117] text-white hover:bg-gray-900 font-black font-mono text-xs sm:text-sm px-5 sm:px-6 py-3 sm:py-3.5 rounded-xl border-3 border-black shadow-[3px_3px_0px_#000] sm:shadow-[4px_4px_0px_#000] flex items-center justify-center gap-2 cursor-pointer transition-all active:translate-x-[2px] active:translate-y-[2px]">
                <Code className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                <span>VIEW REPO</span>
              </button>
            </a>
          </div>
        </main>

        {/* Bottom Ticker Marquee Bar */}
        <div className="bg-black text-[#ffe600] border-t-4 border-black py-2 sm:py-2.5 overflow-hidden font-mono text-[10px] sm:text-xs font-black tracking-widest uppercase z-10 select-none flex">
          <motion.div
            className="flex items-center gap-6 sm:gap-8 whitespace-nowrap shrink-0"
            animate={{ x: ["0%", "-50%"] }}
            transition={{
              ease: "linear",
              duration: 25,
              repeat: Infinity,
            }}
          >
            <span>
              ⚡ UNIVERSAL MULTIMODAL RAG • TECHNICAL BLUEPRINTS & MANUALS • SCIENTIFIC RESEARCH PAPERS •
              ENTERPRISE BOOKS & REPORTS • FOCUSED DIAGRAM & ROI OCR • 100% PRIVATE ON-DEVICE FAISS •
              ZERO DATA LEAKS • HARDWARE ACCELERATED
            </span>
            <span>
              ⚡ UNIVERSAL MULTIMODAL RAG • TECHNICAL BLUEPRINTS & MANUALS • SCIENTIFIC RESEARCH PAPERS •
              ENTERPRISE BOOKS & REPORTS • FOCUSED DIAGRAM & ROI OCR • 100% PRIVATE ON-DEVICE FAISS •
              ZERO DATA LEAKS • HARDWARE ACCELERATED
            </span>
          </motion.div>
        </div>
      </div>

      {/* 
        ========================================================================
        NEO-BRUTALIST 3-CARD SECTION
        ========================================================================
      */}
      <section id="capabilities" className="py-12 sm:py-16 md:py-20 px-4 sm:px-6 max-w-6xl mx-auto space-y-8 sm:space-y-12">
        <div className="text-center space-y-2 sm:space-y-3">
          <h2 className="text-2xl sm:text-4xl md:text-5xl font-black font-sans text-white tracking-tight">
            Engineered for Zero Fluff and Real Grounding
          </h2>
          <p className="text-gray-400 font-mono text-xs sm:text-sm max-w-xl mx-auto px-2">
            Built from scratch for maximum precision, zero cloud latency, and 100% offline privacy.
          </p>
        </div>

        {/* 3 Neo-Brutalist Cards Grid (1 col mobile, 2 col tablet, 3 col desktop) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
          {/* Card 1: MULTIMODAL (Yellow Card) */}
          <div className="bg-[#ffe600] text-black border-4 border-black rounded-2xl sm:rounded-3xl p-5 sm:p-6 flex flex-col justify-between space-y-6 shadow-[5px_5px_0px_#ffffff] sm:shadow-[8px_8px_0px_#ffffff] hover:translate-y-[-4px] transition-transform">
            <div className="space-y-3 sm:space-y-4">
              <div className="flex items-center justify-between border-b-2 border-black pb-2 sm:pb-3">
                <h3 className="text-xl sm:text-2xl font-black font-mono uppercase tracking-tight">
                  MULTIMODAL
                </h3>
                <span className="w-3.5 h-3.5 bg-black rounded-sm" />
              </div>
              <p className="font-mono text-xs font-bold leading-relaxed text-black/90">
                One-shot deep visual scene extraction. Understands photos, diagrams, flowcharts, and
                foreign scripts via local Vision models and sub-region ROI cropping.
              </p>
            </div>

            <div className="bg-white border-2 border-black rounded-xl p-2.5 sm:p-3 font-mono text-xs font-black text-black shadow-[2px_2px_0px_#000] text-center">
              RapidOCR + Local Vision LLM
            </div>
          </div>

          {/* Card 2: GUARDRAILS (Green Card) */}
          <div className="bg-[#22c55e] text-black border-4 border-black rounded-2xl sm:rounded-3xl p-5 sm:p-6 flex flex-col justify-between space-y-6 shadow-[5px_5px_0px_#ffffff] sm:shadow-[8px_8px_0px_#ffffff] hover:translate-y-[-4px] transition-transform">
            <div className="space-y-3 sm:space-y-4">
              <div className="flex items-center justify-between border-b-2 border-black pb-2 sm:pb-3">
                <h3 className="text-xl sm:text-2xl font-black font-mono uppercase tracking-tight">
                  GUARDRAILS
                </h3>
                <span className="w-3.5 h-3.5 bg-black rounded-sm" />
              </div>
              <p className="font-mono text-xs font-bold leading-relaxed text-black/90">
                Strict cosine distance relevance gates and zero-evidence refusal fallbacks ensure
                the engine never hallucinates out-of-context facts.
              </p>
            </div>

            <div className="bg-white border-2 border-black rounded-xl p-2.5 sm:p-3 font-mono text-xs font-black text-black shadow-[2px_2px_0px_#000] text-center">
              Cosine Filter + HyDE Expander
            </div>
          </div>

          {/* Card 3: STANDALONE (Pink Card) */}
          <div className="bg-[#ec4899] text-black border-4 border-black rounded-2xl sm:rounded-3xl p-5 sm:p-6 flex flex-col justify-between space-y-6 shadow-[5px_5px_0px_#ffffff] sm:shadow-[8px_8px_0px_#ffffff] hover:translate-y-[-4px] transition-transform">
            <div className="space-y-3 sm:space-y-4">
              <div className="flex items-center justify-between border-b-2 border-black pb-2 sm:pb-3">
                <h3 className="text-xl sm:text-2xl font-black font-mono uppercase tracking-tight">
                  STANDALONE
                </h3>
                <span className="w-3.5 h-3.5 bg-black rounded-sm" />
              </div>
              <p className="font-mono text-xs font-bold leading-relaxed text-black/90">
                Export a turnkey production bundle containing pre-indexed vector DB, standalone
                FastAPI server, web UI, and launch scripts.
              </p>
            </div>

            <div className="bg-white border-2 border-black rounded-xl p-2.5 sm:p-3 font-mono text-xs font-black text-black shadow-[2px_2px_0px_#000] text-center">
              FastAPI + ChromaDB + Batch
            </div>
          </div>
        </div>
      </section>

      {/* 
        ========================================================================
        ABOUT US SECTION
        ========================================================================
      */}
      <section id="about" className="border-t-4 border-white bg-black py-12 sm:py-16 md:py-20 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8 sm:gap-12 items-center">
          {/* Left Description Column */}
          <div className="space-y-4 sm:space-y-6">
            <h2 className="text-2xl sm:text-3xl font-black font-mono text-white uppercase tracking-wider">
              ABOUT US
            </h2>

            <p className="font-mono text-xs sm:text-sm text-gray-300 font-bold leading-relaxed uppercase">
              THE CREATION OF THE INSIGHTRAG ENGINE WAS DRIVEN BY THE NEED FOR PRIVATE, ZERO-COST,
              AND UNCOMPROMISING LOCAL ARTIFICIAL INTELLIGENCE. WE BUILT A HIGH-PERFORMANCE
              ARCHITECTURE CAPABLE OF PROCESSING MULTI-FORMAT DOCUMENTS, SCANNED MEDICAL RECORDS,
              AND VISUAL MEDIA WITH STRICT ANTI-HALLUCINATION GUARDRAILS AND 1-CLICK STANDALONE
              DEPLOYMENT.
            </p>

            <button
              onClick={handleCopyCLI}
              className="bg-white text-black hover:bg-[#ffe600] font-mono font-black text-xs px-5 sm:px-6 py-2.5 sm:py-3 rounded-full border-2 border-white shadow-[3px_3px_0px_#fff] flex items-center gap-2 cursor-pointer transition-colors active:scale-95"
            >
              {copied ? (
                <Check className="w-4 h-4 text-black" />
              ) : (
                <Copy className="w-4 h-4 text-black" />
              )}
              <span>COPY CLI LAUNCH</span>
            </button>
          </div>

          {/* Right Text Graphic Column */}
          <div className="flex items-center justify-center py-4 sm:py-0">
            <div className="text-5xl sm:text-7xl md:text-8xl lg:text-9xl font-black font-sans tracking-tighter text-transparent bg-clip-text bg-gradient-to-br from-white via-gray-400 to-gray-800 select-none text-center md:text-left">
              INSIGHT
              <br />
              RAG
            </div>
          </div>
        </div>
      </section>

      {/* Bottom Footer (Optimized for mobile & tablet) */}
      <footer className="border-t-2 border-gray-800 bg-black py-6 sm:py-8 px-4 sm:px-6 font-mono text-[11px] sm:text-xs text-gray-400">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-4 text-center sm:text-left">
          <div className="font-bold text-gray-300">
            ⚡ InsightRAG — Autonomous Multimodal RAG Engine
          </div>
          <div className="text-gray-400 py-1 px-3 bg-gray-950 rounded-full border border-gray-800">
            Made by <span className="text-gray-100 font-bold">Karan Pratap Singh</span>
          </div>
          <div className="text-gray-500">
            © {new Date().getFullYear()} InsightRAG AI. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}
