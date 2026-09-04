import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
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
  Box,
  FileText,
  Search,
  ExternalLink,
  Zap,
  HardDrive
} from "lucide-react";

export const Route = createFileRoute("/docs")({
  head: () => ({
    meta: [
      { title: "InsightRAG" },
      {
        name: "description",
        content:
          "Complete documentation for InsightRAG: 1-Line Quickstart, System Architecture, Hardware Auto-Tuning, Multimodal OCR, Privacy Guardrails, Standalone Export, and REST API Reference.",
      },
    ],
  }),
  component: DocsPage,
});

export function DocsPage() {
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState("quickstart");

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCmd(id);
    setTimeout(() => setCopiedCmd(null), 2000);
  };

  const scrollToSection = (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    setActiveSection(id);
    const element = document.getElementById(id);
    if (element) {
      const headerOffset = 90;
      const elementPosition = element.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
      window.scrollTo({
        top: offsetPosition,
        behavior: "smooth"
      });
    }
  };

  // ScrollSpy to automatically highlight active section while scrolling
  useEffect(() => {
    const sectionIds = ["quickstart", "architecture", "hardware", "multimodal", "guardrails", "standalone", "api"];
    const handleScroll = () => {
      const scrollPos = window.scrollY + 120;
      for (let i = sectionIds.length - 1; i >= 0; i--) {
        const el = document.getElementById(sectionIds[i]);
        if (el && el.offsetTop <= scrollPos) {
          setActiveSection(sectionIds[i]);
          break;
        }
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const navGroups = [
    {
      title: "Getting Started",
      items: [
        { id: "quickstart", label: "1-Line Quickstart", icon: Terminal },
        { id: "architecture", label: "Engine Architecture", icon: Layers },
      ],
    },
    {
      title: "Core Capabilities",
      items: [
        { id: "hardware", label: "Hardware Auto-Tuning", icon: Cpu },
        { id: "multimodal", label: "Diagram & Visual Parser", icon: Sparkles },
        { id: "guardrails", label: "Anti-Hallucination & Privacy", icon: Shield },
        { id: "standalone", label: "Standalone Export", icon: Box },
      ],
    },
    {
      title: "Developers",
      items: [
        { id: "api", label: "REST API Reference", icon: Code },
      ],
    },
  ];

  return (
    <div className="min-h-screen bg-[#f4f4f0] text-black font-sans selection:bg-[#ffe600] selection:text-black">
      
      {/* Top Banner & Header */}
      <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b-4 border-black px-4 sm:px-8 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="bg-black text-white font-black font-mono text-base sm:text-lg px-3 py-1 rounded-xl border-2 border-black shadow-[2px_2px_0px_#000] italic tracking-tighter"
            >
              InsightRAG
            </Link>
            <span className="hidden sm:inline-block bg-[#ffe600] font-mono font-bold text-xs px-2.5 py-0.5 rounded-md border-2 border-black">
              DOCS v1.0
            </span>
          </div>

          <div className="flex items-center gap-3 font-mono text-xs font-bold">
            <Link
              to="/"
              className="bg-white hover:bg-gray-100 text-black px-3.5 py-1.5 rounded-xl border-2 border-black shadow-[2px_2px_0px_#000] transition active:translate-x-[1px] active:translate-y-[1px]"
            >
              Home
            </Link>
            <a
              href="https://github.com/SypherKx/InsightRAG"
              target="_blank"
              rel="noreferrer"
              className="bg-black hover:bg-gray-800 text-white px-3.5 py-1.5 rounded-xl border-2 border-black shadow-[2px_2px_0px_#000] transition active:translate-x-[1px] active:translate-y-[1px] flex items-center gap-1.5"
            >
              <Code className="w-3.5 h-3.5" />
              <span>GitHub</span>
            </a>
          </div>
        </div>
      </header>

      {/* Mobile Sticky Quick Navigation (< md) */}
      <div className="md:hidden sticky top-[57px] z-40 bg-white/95 backdrop-blur-md border-b-2 border-black px-4 py-2 overflow-x-auto flex items-center gap-2 shadow-[0_2px_0px_#000]">
        <div className="flex items-center gap-1.5 font-mono text-[11px] font-bold text-gray-500 shrink-0">
          <BookOpen className="w-3.5 h-3.5 text-black" />
          <span>Index:</span>
        </div>
        {navGroups.flatMap(g => g.items).map((item) => (
          <button
            key={item.id}
            onClick={(e) => scrollToSection(e, item.id)}
            className={`whitespace-nowrap px-2.5 py-1 rounded-lg border text-xs font-mono font-bold shrink-0 transition-all ${
              activeSection === item.id
                ? "bg-[#ffe600] text-black border-black shadow-[1px_1px_0px_#000]"
                : "bg-gray-100 text-gray-700 border-gray-300"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* Main Layout: Sidebar + Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-8 py-8 grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
        
        {/* Left Permanently Sticky Sidebar */}
        <aside className="hidden md:block md:col-span-4 lg:col-span-3 md:sticky md:top-20 z-30 self-start">
          <div className="bg-white border-3 border-black rounded-2xl p-5 shadow-[5px_5px_0px_#000] space-y-6 max-h-[calc(100vh-6rem)] overflow-y-auto">
            <div className="font-mono font-black text-xs uppercase tracking-wider text-gray-500 border-b-2 border-black pb-2 flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-black" />
              <span>Documentation Index</span>
            </div>

            {navGroups.map((group) => (
              <div key={group.title} className="space-y-2">
                <div className="font-mono font-bold text-[11px] text-gray-400 uppercase tracking-wider px-2">
                  {group.title}
                </div>
                <div className="space-y-1">
                  {group.items.map((item) => {
                    const Icon = item.icon;
                    const isActive = activeSection === item.id;
                    return (
                      <button
                        key={item.id}
                        onClick={(e) => scrollToSection(e, item.id)}
                        className={`w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-xl border-2 font-mono text-xs font-bold transition-all cursor-pointer ${
                          isActive
                            ? "bg-[#ffe600] text-black border-black shadow-[2px_2px_0px_#000] translate-x-1"
                            : "bg-transparent text-gray-700 border-transparent hover:border-black hover:bg-gray-50"
                        }`}
                      >
                        <Icon className="w-3.5 h-3.5 shrink-0" />
                        <span>{item.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}

            <div className="pt-2 border-t-2 border-black space-y-2">
              <a
                href="https://github.com/SypherKx/InsightRAG"
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-between px-3 py-2 rounded-xl border-2 border-black bg-black text-white hover:bg-gray-800 font-mono text-xs font-bold transition shadow-[2px_2px_0px_#000]"
              >
                <div className="flex items-center gap-2">
                  <Code className="w-3.5 h-3.5" />
                  <span>GitHub Repository</span>
                </div>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>
        </aside>

        {/* Right Documentation Content */}
        <main className="col-span-1 md:col-span-8 lg:col-span-9 space-y-12 min-w-0">
          
          {/* ========================================================================= */}
          {/* 1. QUICKSTART SECTION */}
          {/* ========================================================================= */}
          <section id="quickstart" className="scroll-mt-24 space-y-6">
            <div className="bg-white border-3 border-black rounded-2xl p-6 sm:p-8 shadow-[6px_6px_0px_#000] space-y-6">
              
              <div className="flex items-center gap-2">
                <span className="bg-[#ffe600] text-black font-mono font-black text-xs px-3 py-1 rounded-full border-2 border-black">
                  QUICKSTART
                </span>
                <span className="text-gray-400 font-mono text-xs font-bold">// 1-Line Setup & CLI Installation</span>
              </div>

              <h1 className="text-3xl sm:text-4xl font-black font-mono tracking-tight">
                1-Line Setup & CLI Installation
              </h1>

              <p className="text-sm sm:text-base text-gray-800 leading-relaxed font-sans font-medium">
                <strong>InsightRAG AI</strong> is an autonomous, multimodal local-first RAG generator. It indexes PDFs, Word documents, and images on your machine with zero mandatory API costs. By default, it runs locally with Ollama and on-device embeddings, while offering optional cloud API fallbacks (OpenAI, Gemini, Groq, Claude) whenever you want higher reasoning capabilities.
              </p>

              {/* Windows 1-Line Box */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-xs uppercase tracking-wider text-black flex items-center gap-1.5">
                    <Terminal className="w-4 h-4 text-[#ec4899]" />
                    Windows 1-Line Installer
                  </span>
                  <button
                    onClick={() =>
                      copyToClipboard(
                        `powershell -ExecutionPolicy Bypass -Command "& '$env:USERPROFILE\\OneDrive\\Desktop\\Insight-Forge-master\\Insight-Forge-master\\launch.ps1'"`,
                        "ps1"
                      )
                    }
                    className="flex items-center gap-1 bg-black text-white hover:bg-gray-800 text-[11px] font-mono font-bold px-2.5 py-1 rounded-lg border border-black cursor-pointer shadow-[1px_1px_0px_#000]"
                  >
                    {copiedCmd === "ps1" ? <Check className="w-3 h-3 text-[#ffe600]" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedCmd === "ps1" ? "Copied!" : "Copy"}</span>
                  </button>
                </div>

                <div className="bg-black text-[#ffe600] font-mono text-xs sm:text-sm p-4 rounded-xl border-2 border-black shadow-[3px_3px_0px_#000] overflow-x-auto">
                  <code># Run in PowerShell (Windows 10 or 11)</code><br />
                  <code className="text-white">powershell -ExecutionPolicy Bypass -File .\launch.ps1</code>
                </div>
              </div>

              {/* Manual Git Installation */}
              <div className="space-y-2 pt-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-xs uppercase tracking-wider text-black flex items-center gap-1.5">
                    <Code className="w-4 h-4 text-black" />
                    Manual Installation (Git / All Platforms)
                  </span>
                  <button
                    onClick={() =>
                      copyToClipboard(
                        `git clone https://github.com/SypherKx/InsightRAG.git\ncd InsightRAG\npip install -r requirements.txt\npython scripts/run_local.py`,
                        "git"
                      )
                    }
                    className="flex items-center gap-1 bg-black text-white hover:bg-gray-800 text-[11px] font-mono font-bold px-2.5 py-1 rounded-lg border border-black cursor-pointer shadow-[1px_1px_0px_#000]"
                  >
                    {copiedCmd === "git" ? <Check className="w-3 h-3 text-[#ffe600]" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedCmd === "git" ? "Copied!" : "Copy"}</span>
                  </button>
                </div>

                <div className="bg-gray-900 text-gray-200 font-mono text-xs sm:text-sm p-4 rounded-xl border-2 border-black shadow-[3px_3px_0px_#000] overflow-x-auto space-y-1">
                  <div className="text-gray-500"># Clone and start the factory server</div>
                  <div className="text-green-400">git clone https://github.com/SypherKx/InsightRAG.git</div>
                  <div>cd InsightRAG</div>
                  <div>pip install -r requirements.txt</div>
                  <div className="text-[#ffe600]">python scripts/run_local.py</div>
                </div>
              </div>

              {/* 3 Value Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
                <div className="bg-[#ffe600]/20 border-2 border-black p-4 rounded-xl space-y-1.5 shadow-[3px_3px_0px_#000]">
                  <div className="font-mono font-black text-xs flex items-center gap-1.5 text-black">
                    <Cpu className="w-4 h-4" />
                    Automatic Hardware Check
                  </div>
                  <p className="text-xs text-gray-700 leading-relaxed font-medium">
                    Detects available NVIDIA VRAM, Apple Silicon MPS, or CPU cores to configure quantization.
                  </p>
                </div>

                <div className="bg-sky-50 border-2 border-black p-4 rounded-xl space-y-1.5 shadow-[3px_3px_0px_#000]">
                  <div className="font-mono font-black text-xs flex items-center gap-1.5 text-black">
                    <HardDrive className="w-4 h-4" />
                    Local Weight Caching
                  </div>
                  <p className="text-xs text-gray-700 leading-relaxed font-medium">
                    Downloads lightweight on-device embedding weights (all-MiniLM-L6-v2, 80MB) once.
                  </p>
                </div>

                <div className="bg-pink-50 border-2 border-black p-4 rounded-xl space-y-1.5 shadow-[3px_3px_0px_#000]">
                  <div className="font-mono font-black text-xs flex items-center gap-1.5 text-black">
                    <Zap className="w-4 h-4" />
                    Instant Browser Launch
                  </div>
                  <p className="text-xs text-gray-700 leading-relaxed font-medium">
                    Launches the factory web studio on <code className="bg-black text-white px-1 py-0.5 rounded text-[10px]">http://localhost:5173</code> automatically.
                  </p>
                </div>
              </div>

            </div>
          </section>

          {/* ========================================================================= */}
          {/* 2. SYSTEM ARCHITECTURE SECTION */}
          {/* ========================================================================= */}
          <section id="architecture" className="scroll-mt-24 space-y-6">
            <div className="bg-white border-3 border-black rounded-2xl p-6 sm:p-8 shadow-[6px_6px_0px_#000] space-y-6">
              
              <div className="flex items-center gap-2">
                <span className="bg-black text-white font-mono font-black text-xs px-3 py-1 rounded-full border-2 border-black">
                  SYSTEM ARCHITECTURE
                </span>
                <span className="text-gray-400 font-mono text-xs font-bold">// 4-Stage Pipeline Lifecycle</span>
              </div>

              <h2 className="text-2xl sm:text-3xl font-black font-mono tracking-tight">
                4-Stage Pipeline Lifecycle
              </h2>

              <p className="text-sm text-gray-700 leading-relaxed font-medium">
                InsightRAG AI uses a multi-tier pipeline engineered to prevent hallucinations while extracting textual information, mathematical formulas, and visual diagrams:
              </p>

              {/* 4 Stage Pipeline Cards */}
              <div className="space-y-3 font-mono text-xs">
                
                <div className="bg-white border-2 border-black p-4 rounded-xl shadow-[3px_3px_0px_#000] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="bg-black text-white font-black px-2.5 py-1 rounded-lg text-xs">1</span>
                    <div>
                      <span className="font-black text-sm text-black">INGESTION</span>
                      <div className="text-gray-600 text-xs mt-0.5">PDF / Word / Images → PyMuPDF Vector Clustering + RapidOCR</div>
                    </div>
                  </div>
                  <span className="self-start sm:self-auto bg-[#ffe600] text-black font-bold px-2 py-0.5 rounded border border-black text-[11px]">
                    Semantic Chunks
                  </span>
                </div>

                <div className="bg-white border-2 border-black p-4 rounded-xl shadow-[3px_3px_0px_#000] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="bg-black text-white font-black px-2.5 py-1 rounded-lg text-xs">2</span>
                    <div>
                      <span className="font-black text-sm text-black">EMBEDDING</span>
                      <div className="text-gray-600 text-xs mt-0.5">Local SentenceTransformer → Embedded FAISS / ChromaDB Store</div>
                    </div>
                  </div>
                  <span className="self-start sm:self-auto bg-sky-200 text-black font-bold px-2 py-0.5 rounded border border-black text-[11px]">
                    Vector Store
                  </span>
                </div>

                <div className="bg-white border-2 border-black p-4 rounded-xl shadow-[3px_3px_0px_#000] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="bg-black text-white font-black px-2.5 py-1 rounded-lg text-xs">3</span>
                    <div>
                      <span className="font-black text-sm text-black">RETRIEVAL</span>
                      <div className="text-gray-600 text-xs mt-0.5">Multi-Turn Query Attention + HyDE Expansion</div>
                    </div>
                  </div>
                  <span className="self-start sm:self-auto bg-green-200 text-black font-bold px-2 py-0.5 rounded border border-black text-[11px]">
                    Top-K Chunks
                  </span>
                </div>

                <div className="bg-white border-2 border-black p-4 rounded-xl shadow-[3px_3px_0px_#000] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="bg-black text-white font-black px-2.5 py-1 rounded-lg text-xs">4</span>
                    <div>
                      <span className="font-black text-sm text-black">SYNTHESIS</span>
                      <div className="text-gray-600 text-xs mt-0.5">Local Ollama LLM + Grounding Verification</div>
                    </div>
                  </div>
                  <span className="self-start sm:self-auto bg-[#ec4899] text-white font-bold px-2 py-0.5 rounded border border-black text-[11px]">
                    Answer + Visual Evidence
                  </span>
                </div>

              </div>

            </div>
          </section>

          {/* ========================================================================= */}
          {/* 3. HARDWARE AUTO-TUNING SECTION */}
          {/* ========================================================================= */}
          <section id="hardware" className="scroll-mt-24 space-y-6">
            <div className="bg-white border-3 border-black rounded-2xl p-6 sm:p-8 shadow-[6px_6px_0px_#000] space-y-6">
              
              <div className="flex items-center gap-2">
                <span className="bg-purple-600 text-white font-mono font-black text-xs px-3 py-1 rounded-full border-2 border-black">
                  COMPUTE PROFILING
                </span>
                <span className="text-gray-400 font-mono text-xs font-bold">// Hardware Auto-Tuning</span>
              </div>

              <h2 className="text-2xl sm:text-3xl font-black font-mono tracking-tight">
                Hardware Auto-Tuning
              </h2>

              <p className="text-sm text-gray-700 leading-relaxed font-medium">
                Rather than failing on resource-constrained machines, the hardware engine automatically scales quantization and model parameters to fit your machine's exact specifications:
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                
                <div className="bg-emerald-50 border-2 border-black p-5 rounded-xl space-y-2 shadow-[3px_3px_0px_#000]">
                  <div className="bg-emerald-600 text-white font-mono font-bold text-[10px] px-2 py-0.5 rounded-full inline-block">
                    TIER 1 • HIGH VRAM
                  </div>
                  <div className="font-mono font-black text-sm">High VRAM (≥ 12GB)</div>
                  <p className="text-xs text-gray-700 leading-relaxed">
                    Runs <strong>Qwen2.5 (7B / 14B)</strong> with full context windows and high-resolution visual processing.
                  </p>
                </div>

                <div className="bg-amber-50 border-2 border-black p-5 rounded-xl space-y-2 shadow-[3px_3px_0px_#000]">
                  <div className="bg-amber-600 text-white font-mono font-bold text-[10px] px-2 py-0.5 rounded-full inline-block">
                    TIER 2 • MID-RANGE
                  </div>
                  <div className="font-mono font-black text-sm">Mid-Range (6GB - 11GB)</div>
                  <p className="text-xs text-gray-700 leading-relaxed">
                    Selects <strong>Llama3.2 (3B)</strong> with Q4_K_M quantization for rapid inference and low memory overhead.
                  </p>
                </div>

                <div className="bg-blue-50 border-2 border-black p-5 rounded-xl space-y-2 shadow-[3px_3px_0px_#000]">
                  <div className="bg-blue-600 text-white font-mono font-bold text-[10px] px-2 py-0.5 rounded-full inline-block">
                    TIER 3 • CPU ONLY
                  </div>
                  <div className="font-mono font-black text-sm">CPU Only / Ultrabook</div>
                  <p className="text-xs text-gray-700 leading-relaxed">
                    Employs <strong>CPU ONNX runtime</strong>, multi-threaded batching, and lightweight 1.5B/3B models.
                  </p>
                </div>

              </div>

            </div>
          </section>

          {/* ========================================================================= */}
          {/* 4. MULTIMODAL VECTOR DIAGRAM PARSER */}
          {/* ========================================================================= */}
          <section id="multimodal" className="scroll-mt-24 space-y-6">
            <div className="bg-white border-3 border-black rounded-2xl p-6 sm:p-8 shadow-[6px_6px_0px_#000] space-y-6">
              
              <div className="flex items-center gap-2">
                <span className="bg-[#ec4899] text-white font-mono font-black text-xs px-3 py-1 rounded-full border-2 border-black">
                  MULTIMODAL
                </span>
                <span className="text-gray-400 font-mono text-xs font-bold">// Vector Diagram & OCR Parser</span>
              </div>

              <h2 className="text-2xl sm:text-3xl font-black font-mono tracking-tight">
                Vector Diagram & OCR Parser
              </h2>

              <p className="text-sm text-gray-700 leading-relaxed font-medium">
                Standard RAG solutions discard charts, flowcharts, and math formulas by stripping PDFs down to plain text. InsightRAG AI uses an object-level layout detector to isolate, crop, and index diagrams alongside text.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
                
                <div className="bg-white border-2 border-black p-4 rounded-xl space-y-2 shadow-[3px_3px_0px_#000]">
                  <div className="font-black text-sm text-black flex items-center gap-1.5">
                    <Layers className="w-4 h-4 text-purple-600" />
                    Vector Shape Clustering
                  </div>
                  <p className="text-gray-600 leading-relaxed">
                    Detects architectural diagrams, graphs, and drawings from raw page vectors.
                  </p>
                </div>

                <div className="bg-white border-2 border-black p-4 rounded-xl space-y-2 shadow-[3px_3px_0px_#000]">
                  <div className="font-black text-sm text-black flex items-center gap-1.5">
                    <FileText className="w-4 h-4 text-blue-600" />
                    Proximity Caption Matching
                  </div>
                  <p className="text-gray-600 leading-relaxed">
                    Matches diagram bounding boxes to nearby figure captions (e.g. <em>Figure 2: Architecture Overview</em>).
                  </p>
                </div>

                <div className="bg-white border-2 border-black p-4 rounded-xl space-y-2 shadow-[3px_3px_0px_#000]">
                  <div className="font-black text-sm text-black flex items-center gap-1.5">
                    <Search className="w-4 h-4 text-pink-600" />
                    Reverse Image Search
                  </div>
                  <p className="text-gray-600 leading-relaxed">
                    Allows users to paste or upload an image (Ctrl+V) to find matching diagrams and formulas across documents.
                  </p>
                </div>

              </div>

            </div>
          </section>

          {/* ========================================================================= */}
          {/* 5. PRIVACY & GUARDRAILS SECTION */}
          {/* ========================================================================= */}
          <section id="guardrails" className="scroll-mt-24 space-y-6">
            <div className="bg-white border-3 border-black rounded-2xl p-6 sm:p-8 shadow-[6px_6px_0px_#000] space-y-6">
              
              <div className="flex items-center gap-2">
                <span className="bg-emerald-600 text-white font-mono font-black text-xs px-3 py-1 rounded-full border-2 border-black">
                  PRIVACY & GUARDRAILS
                </span>
                <span className="text-gray-400 font-mono text-xs font-bold">// Anti-Hallucination & Local Privacy</span>
              </div>

              <h2 className="text-2xl sm:text-3xl font-black font-mono tracking-tight">
                Anti-Hallucination & Local-First Privacy
              </h2>

              <p className="text-sm text-gray-700 leading-relaxed font-medium">
                Cloud models frequently reject sensitive or proprietary documents due to third-party data transmission policies. InsightRAG AI provides a local-first pipeline where document chunking, visual layout detection, and vector indexing always remain private on your machine, with optional BYOK cloud models for synthesis.
              </p>

              <div className="bg-gray-50 border-2 border-black p-5 rounded-xl space-y-3 shadow-[3px_3px_0px_#000]">
                <div className="flex items-center gap-2 font-mono font-black text-sm text-black">
                  <Shield className="w-4 h-4 text-emerald-600" />
                  Anti-Hallucination Verification
                </div>
                <p className="text-xs sm:text-sm text-gray-700 leading-relaxed">
                  Every generated response is cross-checked against retrieved source chunks. Answers unsupported by source text are flagged with confidence metrics and grounded badges.
                </p>
              </div>

            </div>
          </section>

          {/* ========================================================================= */}
          {/* 6. STANDALONE EXPORT SECTION */}
          {/* ========================================================================= */}
          <section id="standalone" className="scroll-mt-24 space-y-6">
            <div className="bg-white border-3 border-black rounded-2xl p-6 sm:p-8 shadow-[6px_6px_0px_#000] space-y-6">
              
              <div className="flex items-center gap-2">
                <span className="bg-blue-600 text-white font-mono font-black text-xs px-3 py-1 rounded-full border-2 border-black">
                  DEPLOYMENT
                </span>
                <span className="text-gray-400 font-mono text-xs font-bold">// Turnkey Standalone Export</span>
              </div>

              <h2 className="text-2xl sm:text-3xl font-black font-mono tracking-tight">
                Turnkey Standalone Export
              </h2>

              <p className="text-sm text-gray-700 leading-relaxed font-medium">
                Once your knowledge base is indexed in the factory studio, you can export a self-contained ZIP bundle that operates standalone on local hardware with zero external dependencies:
              </p>

              <div className="space-y-3 font-mono text-xs">
                <div className="font-bold text-xs text-gray-500 uppercase">What's Inside the Exported Bundle:</div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="bg-white border-2 border-black p-3.5 rounded-xl shadow-[2px_2px_0px_#000] space-y-1">
                    <span className="font-bold text-black text-sm">vector_db/</span>
                    <p className="text-gray-600 text-xs">Pre-indexed ChromaDB / FAISS vector database with all document embeddings.</p>
                  </div>

                  <div className="bg-white border-2 border-black p-3.5 rounded-xl shadow-[2px_2px_0px_#000] space-y-1">
                    <span className="font-bold text-black text-sm">images/</span>
                    <p className="text-gray-600 text-xs">Extracted high-resolution diagram crops and figures ready for visual search.</p>
                  </div>

                  <div className="bg-white border-2 border-black p-3.5 rounded-xl shadow-[2px_2px_0px_#000] space-y-1">
                    <span className="font-bold text-black text-sm">run.bat & run.sh</span>
                    <p className="text-gray-600 text-xs">1-click launchers with system package cache detection for startup under 0.1s.</p>
                  </div>

                  <div className="bg-white border-2 border-black p-3.5 rounded-xl shadow-[2px_2px_0px_#000] space-y-1">
                    <span className="font-bold text-black text-sm">server.py & index.html</span>
                    <p className="text-gray-600 text-xs">Standalone FastAPI microservice with persistent LocalStorage auto-save and Quit controls.</p>
                  </div>
                </div>
              </div>

              {/* Running standalone code box */}
              <div className="space-y-2 pt-2">
                <div className="font-mono font-bold text-xs text-black uppercase">Running Your Standalone Package</div>
                <div className="bg-black text-[#ffe600] font-mono text-xs p-4 rounded-xl border-2 border-black shadow-[3px_3px_0px_#000] space-y-1">
                  <div className="text-gray-500"># On Windows: Double-click or run from terminal</div>
                  <div className="text-white">run.bat</div>
                  <div className="text-gray-500 pt-2"># On Linux or macOS:</div>
                  <div className="text-white">chmod +x run.sh && ./run.sh</div>
                </div>
              </div>

            </div>
          </section>

          {/* ========================================================================= */}
          {/* 7. REST API REFERENCE SECTION */}
          {/* ========================================================================= */}
          <section id="api" className="scroll-mt-24 space-y-6">
            <div className="bg-white border-3 border-black rounded-2xl p-6 sm:p-8 shadow-[6px_6px_0px_#000] space-y-6">
              
              <div className="flex items-center gap-2">
                <span className="bg-yellow-400 text-black font-mono font-black text-xs px-3 py-1 rounded-full border-2 border-black">
                  DEVELOPERS
                </span>
                <span className="text-gray-400 font-mono text-xs font-bold">// REST API Reference</span>
              </div>

              <h2 className="text-2xl sm:text-3xl font-black font-mono tracking-tight">
                REST API Reference
              </h2>

              <p className="text-sm text-gray-700 leading-relaxed font-medium">
                Integrate the InsightRAG engine into your own frontends, Discord bots, or internal tools using the standard REST API:
              </p>

              {/* API Table */}
              <div className="border-2 border-black rounded-xl overflow-hidden shadow-[3px_3px_0px_#000]">
                <div className="overflow-x-auto">
                  <table className="w-full text-left font-mono text-xs">
                    <thead className="bg-black text-white uppercase text-[11px] font-bold">
                      <tr>
                        <th className="p-3 border-r border-gray-700 w-24">Method</th>
                        <th className="p-3 border-r border-gray-700">Endpoint</th>
                        <th className="p-3">Description</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y-2 divide-black bg-white font-medium">
                      <tr>
                        <td className="p-3 border-r-2 border-black">
                          <span className="bg-green-100 text-green-800 font-black px-2 py-0.5 rounded border border-green-800">
                            POST
                          </span>
                        </td>
                        <td className="p-3 border-r-2 border-black font-bold">/api/sessions/create</td>
                        <td className="p-3 text-gray-700">Creates an isolated RAG session with private vector storage.</td>
                      </tr>
                      <tr>
                        <td className="p-3 border-r-2 border-black">
                          <span className="bg-green-100 text-green-800 font-black px-2 py-0.5 rounded border border-green-800">
                            POST
                          </span>
                        </td>
                        <td className="p-3 border-r-2 border-black font-bold">/api/sessions/&#123;id&#125;/upload</td>
                        <td className="p-3 text-gray-700">Uploads and parses a PDF, Word document, or image.</td>
                      </tr>
                      <tr>
                        <td className="p-3 border-r-2 border-black">
                          <span className="bg-green-100 text-green-800 font-black px-2 py-0.5 rounded border border-green-800">
                            POST
                          </span>
                        </td>
                        <td className="p-3 border-r-2 border-black font-bold">/api/sessions/&#123;id&#125;/chat</td>
                        <td className="p-3 text-gray-700">Submits a query with multi-turn memory and diagram matching.</td>
                      </tr>
                      <tr>
                        <td className="p-3 border-r-2 border-black">
                          <span className="bg-blue-100 text-blue-800 font-black px-2 py-0.5 rounded border border-blue-800">
                            GET
                          </span>
                        </td>
                        <td className="p-3 border-r-2 border-black font-bold">/api/sessions/&#123;id&#125;/export</td>
                        <td className="p-3 text-gray-700">Exports the turnkey standalone ZIP package.</td>
                      </tr>
                      <tr>
                        <td className="p-3 border-r-2 border-black">
                          <span className="bg-green-100 text-green-800 font-black px-2 py-0.5 rounded border border-green-800">
                            POST
                          </span>
                        </td>
                        <td className="p-3 border-r-2 border-black font-bold">/api/shutdown</td>
                        <td className="p-3 text-gray-700">Gracefully stops and halts the local standalone server.</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          </section>

          {/* ========================================================================= */}
          {/* BOTTOM FOOTER */}
          {/* ========================================================================= */}
          <footer className="border-3 border-black bg-white p-5 rounded-2xl shadow-[4px_4px_0px_#000] flex flex-col sm:flex-row items-center justify-between gap-4 font-mono text-xs text-gray-700">
            <div className="font-bold text-black">
              InsightRAG Autonomous Multimodal RAG Engine
            </div>
            <div>
              Made by <span className="font-bold text-black">Karan Pratap Singh</span>
            </div>
            <div className="text-gray-500">
              MIT License • Local First
            </div>
          </footer>

        </main>
      </div>

    </div>
  );
}
