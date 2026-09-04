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
  Code
} from "lucide-react";


export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "InsightRAG AI — Healthcare & Education Autonomous Multimodal RAG" },
      {
        name: "description",
        content:
          "Turn clinical guidelines, medical records, research papers, and university curricula into a turnkey, anti-hallucination local AI knowledge studio with 100% on-device privacy.",
      },
    ],
  }),
  component: LandingPage,
});

export function LandingPage() {
  const [copied, setCopied] = useState(false);
  const cliCommand = `powershell -ExecutionPolicy Bypass -Command "& '$env:USERPROFILE\\OneDrive\\Desktop\\Insight-Forge-master\\Insight-Forge-master\\launch.ps1'"`;

  const handleCopyCLI = () => {
    navigator.clipboard.writeText(cliCommand);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-black text-white font-sans selection:bg-[#ffe600] selection:text-black">
      
      {/* 
        ========================================================================
        HERO SECTION (Image 2 & 5 Style - Sky Noise Textured Background)
        ========================================================================
      */}
      <div
        className="relative bg-cover bg-center bg-no-repeat border-b-4 border-black min-h-[92vh] flex flex-col justify-between"
        style={{
          backgroundImage: `url('/assets/skytextured.jpg'), url('/skytextured.jpg')`,
          backgroundColor: '#86b0d9',
        }}
      >
        {/* Top Navbar */}
        <header className="p-4 sm:p-6 max-w-7xl mx-auto w-full flex items-center justify-between gap-4 z-20">
          
          {/* Logo */}
          <div className="flex items-center gap-2">
            <span className="bg-black text-white font-black font-mono text-lg sm:text-xl px-3 py-1.5 rounded-xl border-2 border-black shadow-[3px_3px_0px_#000] italic tracking-tighter">
              InsightRAG
            </span>
          </div>

          {/* Navigation Pill */}
          <nav className="hidden md:flex items-center gap-6 bg-white/90 backdrop-blur-md px-6 py-2 rounded-full border-2 border-black shadow-[3px_3px_0px_#000] font-mono text-xs font-bold text-black">
            <a href="#capabilities" className="hover:underline">Capabilities</a>
            <Link to="/docs" className="hover:underline text-black font-black">Docs</Link>
            <a href="https://github.com/SypherKx/InsightRAG" target="_blank" rel="noreferrer" className="hover:underline flex items-center gap-1">
              <Code className="w-3.5 h-3.5" />
              GitHub
            </a>
          </nav>

          {/* Top Right Action Button */}
          <button
            onClick={handleCopyCLI}
            className="bg-[#ec4899] text-white hover:bg-pink-600 font-mono font-black text-xs px-4 py-2.5 rounded-xl border-2 border-black shadow-[3px_3px_0px_#000] flex items-center gap-2 cursor-pointer transition-all active:translate-x-[2px] active:translate-y-[2px]"
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            <span>COPY CLI LAUNCH</span>
          </button>
        </header>

        {/* Hero Central Content */}
        <main className="max-w-4xl mx-auto px-4 py-12 text-center space-y-6 z-10 my-auto">
          
          {/* Eyebrow Badge */}
          <div className="inline-block bg-black text-[#ffe600] font-mono font-black text-xs px-4 py-1.5 rounded-full border-2 border-black shadow-[3px_3px_0px_#000] uppercase tracking-wider">
            CLINICAL & ACADEMIC MULTIMODAL RAG FACTORY
          </div>

          {/* Display Headline (Image 2 style with outline drop shadow) */}
          <h1 className="text-4xl sm:text-6xl md:text-7xl font-black font-sans text-black tracking-tight leading-[1.05] drop-shadow-[0_4px_0_rgba(255,255,255,0.8)]">
            Autonomous Multimodal <br />
            <span className="bg-[#ffe600] text-black px-2 py-0.5 rounded border-2 border-black inline-block shadow-[4px_4px_0px_#000] mt-1">
              RAG-in-a-Box Factory
            </span>
          </h1>

          {/* Subtitle */}
          <p className="max-w-2xl mx-auto text-black font-mono font-bold text-sm sm:text-base leading-relaxed bg-white/70 backdrop-blur-sm p-3 rounded-xl border-2 border-black shadow-[3px_3px_0px_#000]">
            Turn complex clinical guidelines, diagnostic diagrams, PubMed research papers, and university curricula into a turnkey, anti-hallucination AI knowledge studio in seconds.
          </p>

          {/* Interactive Command Box */}
          <div className="max-w-2xl mx-auto bg-black text-white p-3 sm:p-4 rounded-2xl border-2 border-black shadow-[6px_6px_0px_#000] space-y-3 font-mono text-xs sm:text-sm">
            <div className="text-gray-400 text-[10px] uppercase tracking-widest">Open PowerShell → cd into project folder → paste:</div>
            <div className="flex items-center gap-2 justify-between bg-[#0d1117] rounded-xl px-3 py-2">
              <div className="flex items-center gap-2 overflow-x-auto text-emerald-400 font-bold flex-1 min-w-0">
                <span className="text-gray-500 flex-shrink-0">PS&gt;</span>
                <code className="whitespace-nowrap text-[11px] sm:text-xs">powershell -ExecutionPolicy Bypass -File .\launch.ps1</code>
              </div>
              <button
                onClick={handleCopyCLI}
                className="bg-[#ffe600] text-black font-black font-mono text-xs px-3 py-1.5 rounded-lg border-2 border-black hover:bg-yellow-400 cursor-pointer flex-shrink-0 flex items-center gap-1 ml-2"
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? "COPIED!" : "COPY"}</span>
              </button>
            </div>
            <div className="text-gray-500 text-[10px] leading-relaxed">
              📁 First navigate to project folder:<br />
              <span className="text-gray-300">cd "$env:USERPROFILE\OneDrive\Desktop\Insight-Forge-master\Insight-Forge-master"</span>
            </div>
          </div>


          {/* Action Buttons */}
          <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
            <Link to="/docs">
              <button className="bg-[#ffe600] text-black hover:bg-yellow-400 font-black font-mono text-sm px-6 py-3.5 rounded-xl border-3 border-black shadow-[4px_4px_0px_#000] flex items-center gap-2 cursor-pointer transition-all active:translate-x-[2px] active:translate-y-[2px]">
                <BookOpen className="w-5 h-5 text-black" />
                <span>EXPLORE DOCUMENTATION</span>
                <ArrowRight className="w-4 h-4 text-black" />
              </button>
            </Link>

            <button
              onClick={handleCopyCLI}
              className="bg-white text-black hover:bg-gray-100 font-black font-mono text-sm px-6 py-3.5 rounded-xl border-3 border-black shadow-[4px_4px_0px_#000] flex items-center gap-2 cursor-pointer transition-all active:translate-x-[2px] active:translate-y-[2px]"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Terminal className="w-4 h-4 text-black" />}
              <span>{copied ? "CLI COMMAND COPIED!" : "COPY CLI LAUNCH"}</span>
            </button>
          </div>

        </main>

        {/* Bottom Ticker Marquee Bar (Infinite Scrolling Motion) */}
        <div className="bg-black text-[#ffe600] border-t-4 border-black py-2.5 overflow-hidden font-mono text-xs font-black tracking-widest uppercase z-10 select-none flex">
          <motion.div
            className="flex items-center gap-8 whitespace-nowrap shrink-0"
            animate={{ x: ["0%", "-50%"] }}
            transition={{
              ease: "linear",
              duration: 25,
              repeat: Infinity,
            }}
          >
            <span>⚡ CLINICAL GUIDELINES & MEDICAL RAG • PUBMED RESEARCH INTELLIGENCE • UNIVERSITY CURRICULA & TEXTBOOKS • MULTIMODAL DIAGNOSTIC OCR • 100% PRIVATE ON-DEVICE FAISS • ZERO DATA LEAKS • HARDWARE ACCELERATED</span>
            <span>⚡ CLINICAL GUIDELINES & MEDICAL RAG • PUBMED RESEARCH INTELLIGENCE • UNIVERSITY CURRICULA & TEXTBOOKS • MULTIMODAL DIAGNOSTIC OCR • 100% PRIVATE ON-DEVICE FAISS • ZERO DATA LEAKS • HARDWARE ACCELERATED</span>
            <span>⚡ CLINICAL GUIDELINES & MEDICAL RAG • PUBMED RESEARCH INTELLIGENCE • UNIVERSITY CURRICULA & TEXTBOOKS • MULTIMODAL DIAGNOSTIC OCR • 100% PRIVATE ON-DEVICE FAISS • ZERO DATA LEAKS • HARDWARE ACCELERATED</span>
            <span>⚡ CLINICAL GUIDELINES & MEDICAL RAG • PUBMED RESEARCH INTELLIGENCE • UNIVERSITY CURRICULA & TEXTBOOKS • MULTIMODAL DIAGNOSTIC OCR • 100% PRIVATE ON-DEVICE FAISS • ZERO DATA LEAKS • HARDWARE ACCELERATED</span>
          </motion.div>
        </div>

      </div>

      {/* 
        ========================================================================
        NEO-BRUTALIST 3-CARD SECTION (Image 1 Style)
        ========================================================================
      */}
      <section id="capabilities" className="py-20 px-6 max-w-6xl mx-auto space-y-12">
        
        <div className="text-center space-y-3">
          <h2 className="text-3xl sm:text-5xl font-black font-sans text-white tracking-tight">
            Engineered for Zero Fluff and Real Grounding
          </h2>
          <p className="text-gray-400 font-mono text-sm max-w-xl mx-auto">
            Built from scratch for maximum precision, zero cloud latency, and 100% offline privacy.
          </p>
        </div>

        {/* 3 Neo-Brutalist Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          
          {/* Card 1: MULTIMODAL (Yellow Card) */}
          <div className="bg-[#ffe600] text-black border-4 border-black rounded-3xl p-6 flex flex-col justify-between space-y-6 shadow-[8px_8px_0px_#ffffff] hover:translate-y-[-4px] transition-transform">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b-2 border-black pb-3">
                <h3 className="text-2xl font-black font-mono uppercase tracking-tight">MULTIMODAL</h3>
                <span className="w-3.5 h-3.5 bg-black rounded-sm" />
              </div>
              <p className="font-mono text-xs font-bold leading-relaxed text-black/90">
                One-shot deep visual scene extraction. Understands photos, diagrams, flowcharts, and foreign scripts via local Vision models.
              </p>
            </div>

            <div className="bg-white border-2 border-black rounded-xl p-3 font-mono text-xs font-black text-black shadow-[2px_2px_0px_#000] text-center">
              RapidOCR + Local Vision LLM
            </div>
          </div>

          {/* Card 2: GUARDRAILS (Green Card) */}
          <div className="bg-[#22c55e] text-black border-4 border-black rounded-3xl p-6 flex flex-col justify-between space-y-6 shadow-[8px_8px_0px_#ffffff] hover:translate-y-[-4px] transition-transform">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b-2 border-black pb-3">
                <h3 className="text-2xl font-black font-mono uppercase tracking-tight">GUARDRAILS</h3>
                <span className="w-3.5 h-3.5 bg-black rounded-sm" />
              </div>
              <p className="font-mono text-xs font-bold leading-relaxed text-black/90">
                Strict cosine distance relevance gates and zero-evidence refusal fallbacks ensure the engine never hallucinates out-of-context facts.
              </p>
            </div>

            <div className="bg-white border-2 border-black rounded-xl p-3 font-mono text-xs font-black text-black shadow-[2px_2px_0px_#000] text-center">
              Cosine Filter + HyDE Expander
            </div>
          </div>

          {/* Card 3: STANDALONE (Pink Card) */}
          <div className="bg-[#ec4899] text-black border-4 border-black rounded-3xl p-6 flex flex-col justify-between space-y-6 shadow-[8px_8px_0px_#ffffff] hover:translate-y-[-4px] transition-transform">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b-2 border-black pb-3">
                <h3 className="text-2xl font-black font-mono uppercase tracking-tight">STANDALONE</h3>
                <span className="w-3.5 h-3.5 bg-black rounded-sm" />
              </div>
              <p className="font-mono text-xs font-bold leading-relaxed text-black/90">
                Export a turnkey production bundle containing pre-indexed vector DB, standalone FastAPI server, web UI, and launch scripts.
              </p>
            </div>

            <div className="bg-white border-2 border-black rounded-xl p-3 font-mono text-xs font-black text-black shadow-[2px_2px_0px_#000] text-center">
              FastAPI + ChromaDB + Batch
            </div>
          </div>

        </div>

      </section>

      {/* 
        ========================================================================
        ABOUT US SECTION (Image 1 Style)
        ========================================================================
      */}
      <section id="about" className="border-t-4 border-white bg-black py-20 px-6">
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
          
          {/* Left Description Column */}
          <div className="space-y-6">
            <h2 className="text-3xl font-black font-mono text-white uppercase tracking-wider">
              ABOUT US
            </h2>

            <p className="font-mono text-xs sm:text-sm text-gray-300 font-bold leading-relaxed uppercase">
              THE CREATION OF THE INSIGHTRAG ENGINE WAS DRIVEN BY THE NEED FOR PRIVATE, ZERO-COST, AND UNCOMPROMISING LOCAL ARTIFICIAL INTELLIGENCE. WE BUILT A HIGH-PERFORMANCE ARCHITECTURE CAPABLE OF PROCESSING MULTI-FORMAT DOCUMENTS, SCANNED MEDICAL RECORDS, AND VISUAL MEDIA WITH STRICT ANTI-HALLUCINATION GUARDRAILS AND 1-CLICK STANDALONE DEPLOYMENT.
            </p>

            <button
              onClick={handleCopyCLI}
              className="bg-white text-black hover:bg-[#ffe600] font-mono font-black text-xs px-6 py-3 rounded-full border-2 border-white shadow-[3px_3px_0px_#fff] flex items-center gap-2 cursor-pointer transition-colors"
            >
              {copied ? <Check className="w-4 h-4 text-black" /> : <Copy className="w-4 h-4 text-black" />}
              <span>COPY CLI LAUNCH</span>
            </button>
          </div>

          {/* Right Text Graphic Column */}
          <div className="flex items-center justify-center">
            <div className="text-6xl sm:text-8xl md:text-9xl font-black font-sans tracking-tighter text-transparent bg-clip-text bg-gradient-to-br from-white via-gray-400 to-gray-800 select-none">
              INSIGHT<br />RAG
            </div>
          </div>

        </div>
      </section>

      {/* Bottom Footer */}
      <footer className="border-t-2 border-gray-800 bg-black py-6 px-6 font-mono text-xs text-gray-400">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>InsightRAG — Autonomous Multimodal RAG Engine</div>
          <div className="text-gray-400">
            Made by <span className="text-gray-200">Karan Pratap Singh</span>
          </div>
          <div>© {new Date().getFullYear()} InsightRAG AI. All rights reserved.</div>
        </div>
      </footer>

    </div>
  );
}
