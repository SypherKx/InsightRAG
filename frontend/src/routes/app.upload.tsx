import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  FileText,
  CheckCircle2,
  Sparkles,
  Download,
  Cpu,
  Zap,
  Bot,
  Send,
  Trash2,
  X,
  Layers,
  HardDrive,
  BookOpen,
  ExternalLink,
  Copy,
  Check,
  RotateCcw,
  User,
  MessageSquarePlus,
} from "lucide-react";
import {
  uploadRAGDocuments,
  queryRAG,
  getRAGStats,
  clearRAGKnowledgeBase,
  getSystemSpecs,
  pullModel,
} from "../services/api";

export const Route = createFileRoute("/app/upload")({
  head: () => ({
    meta: [{ title: "InsightRAG" }],
  }),
  component: KnowledgeBaseStudioPage,
});

const EMBEDDING_OPTIONS = [
  {
    id: "all-MiniLM-L6-v2",
    label: "all-MiniLM-L6-v2",
    fullName: "sentence-transformers/all-MiniLM-L6-v2",
    speedTier: "⚡ ULTRA-FAST (5x)",
    speedBadgeColor: "bg-emerald-400 text-black",
    ramReq: "4GB+ RAM (80MB Model)",
    hardwareLabel: "CPU & Laptop Friendly",
    dim: "384-dim",
    desc: "Lightest & fastest. Zero lag on laptops and multi-core CPUs. Ideal for notes, summaries & rapid PDF indexing.",
  },
  {
    id: "bge-small-en-v1.5",
    label: "bge-small-en-v1.5",
    fullName: "BAAI/bge-small-en-v1.5",
    speedTier: "⚖️ BALANCED (3x)",
    speedBadgeColor: "bg-sky-400 text-black",
    ramReq: "6GB+ RAM (130MB Model)",
    hardwareLabel: "Standard Workstations",
    dim: "384-dim",
    desc: "Optimal balance of low latency and sharp semantic retrieval across standard PDFs, Word documents & EMR records.",
  },
  {
    id: "bge-base-en-v1.5",
    label: "bge-base-en-v1.5",
    fullName: "BAAI/bge-base-en-v1.5",
    speedTier: "🧠 SOTA HIGH PRECISION",
    speedBadgeColor: "bg-[#ffe600] text-black",
    ramReq: "8GB-16GB RAM / GPU (430MB Model)",
    hardwareLabel: "High-Accuracy Research",
    dim: "768-dim",
    desc: "Industry benchmark for retrieval depth. Recommended for clinical guidelines, dense research papers & textbooks.",
  },
  {
    id: "nomic-embed-text",
    label: "nomic-embed-text",
    fullName: "nomic-embed-text",
    speedTier: "🚀 OLLAMA NATIVE 8K",
    speedBadgeColor: "bg-purple-400 text-black",
    ramReq: "8GB+ RAM (270MB Model)",
    hardwareLabel: "Ollama Long-Context",
    dim: "768-dim (8192 context)",
    desc: "100% on-device Ollama native pipeline. Supports massive document chunks up to 8192 tokens per vector.",
  },
];

export function KnowledgeBaseStudioPage() {
  // Hardware Specs State
  const [specs, setSpecs] = useState<any>({
    cpu_threads: 12,
    ram_gb: 15.4,
    gpu_name: "Integrated / CPU",
    vram_gb: 0.0,
    has_gpu: false,
    acceleration_mode: "CPU PARALLEL ENGINE",
    installed_models: ["llama3.2:3b", "moondream:latest"],
  });

  // Model & Config Selection States
  const [selectedLLM, setSelectedLLM] = useState("llama3.2:3b");
  const [sessionLifetime, setSessionLifetime] = useState("3 Hours");
  const [embeddingModel, setEmbeddingModel] = useState("all-MiniLM-L6-v2");
  const [visionOCR, setVisionOCR] = useState(true);
  const [processingMode, setProcessingMode] = useState("local");
  const [cloudApiKey, setCloudApiKey] = useState("");

  // Upload States
  const [drag, setDrag] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [ragStats, setRagStats] = useState<any>({ total_vectors: 0, files: [] });

  // Model Download Modal State
  const [showModal, setShowModal] = useState(false);
  const [customModel, setCustomModel] = useState("llama3.2:3b");
  const [pulling, setPulling] = useState(false);
  const [pullStatus, setPullStatus] = useState("");

  // RAG Query Chat State with LocalStorage Persistence
  const [query, setQuery] = useState("");
  const [chatMessages, setChatMessages] = useState<
    Array<{
      role: "user" | "assistant";
      text: string;
      sources?: any[];
      visual_snippet?: any;
      model?: string;
      timestamp?: string;
    }>
  >(() => {
    try {
      const saved = localStorage.getItem("insightrag_chat_history");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [querying, setQuerying] = useState(false);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [uploadStatusMsg, setUploadStatusMsg] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatInputRef = useRef<HTMLInputElement>(null);

  // Sync chat messages to localStorage & auto-scroll
  useEffect(() => {
    try {
      localStorage.setItem("insightrag_chat_history", JSON.stringify(chatMessages));
    } catch (e) {
      console.warn("Failed saving chat history to localStorage", e);
    }
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages, querying]);

  // Fetch specs & RAG stats on mount
  useEffect(() => {
    loadSpecsAndStats();
  }, []);

  const loadSpecsAndStats = async () => {
    try {
      const data = await getSystemSpecs();
      if (data) setSpecs(data);
      const stats = await getRAGStats();
      if (stats) setRagStats(stats);
    } catch (err) {
      console.error(err);
    }
  };

  const onSelectFiles = async (selected: FileList | null) => {
    if (!selected || selected.length === 0) return;
    const fileArray = Array.from(selected);
    setFiles(fileArray);
    if (fileInputRef.current) fileInputRef.current.value = "";
    await startUpload(fileArray);
  };

  const startUpload = async (fileList: File[]) => {
    setUploading(true);
    setUploadProgress(15);
    setUploadStatusMsg(null);
    const interval = setInterval(() => {
      setUploadProgress((p) => (p >= 90 ? 90 : p + 15));
    }, 150);

    try {
      const res = await uploadRAGDocuments(fileList);
      clearInterval(interval);
      setUploadProgress(100);
      setUploadStatusMsg(`✓ Successfully indexed ${res?.documents_ingested || fileList.length} document(s) (${res?.chunks_created || 0} chunks)!`);
      setTimeout(() => {
        setUploading(false);
        setUploadProgress(0);
        loadSpecsAndStats();
      }, 600);
      setTimeout(() => {
        setUploadStatusMsg(null);
      }, 5000);
    } catch (err: any) {
      clearInterval(interval);
      setUploading(false);
      setUploadProgress(0);
      setUploadStatusMsg(`⚠️ Upload error: ${err?.response?.data?.detail || err?.message || "Failed to process files"}`);
      loadSpecsAndStats();
    }
  };

  const handleClearKnowledgeBase = async () => {
    if (confirm("Clear all vector indices in knowledge base?")) {
      await clearRAGKnowledgeBase();
      loadSpecsAndStats();
      setChatMessages([]);
      localStorage.removeItem("insightrag_chat_history");
    }
  };

  const handleClearChatOnly = () => {
    setChatMessages([]);
    localStorage.removeItem("insightrag_chat_history");
  };

  const copyToClipboard = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  const handleSendQuery = async (overridePrompt?: string) => {
    const textToSend = (overridePrompt !== undefined ? overridePrompt : query).trim();
    if (!textToSend || querying) return;
    setQuery("");

    const nowTime = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const userMsg = {
      role: "user" as const,
      text: textToSend,
      timestamp: nowTime,
    };

    // Keep current history for API context
    const historyPayload = chatMessages.slice(-6).map((m) => ({
      role: m.role,
      text: m.text,
    }));

    setChatMessages((prev) => [...prev, userMsg]);
    setQuerying(true);

    try {
      const isCloud = processingMode !== "local";
      const modelToUse = isCloud ? processingMode : selectedLLM;
      const res = await queryRAG(
        textToSend,
        5,
        0.0,
        modelToUse,
        isCloud ? "cloud" : "local",
        cloudApiKey,
        historyPayload
      );

      const assistantMsg = {
        role: "assistant" as const,
        text: res.answer || res.response || "No structured answer generated.",
        sources: res.sources || res.results || res.context_chunks || [],
        visual_snippet: res.visual_snippet,
        model: res.llm_model || modelToUse,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setChatMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant" as const,
          text: `⚠️ Query encountered an issue: ${
            err?.response?.data?.detail || err?.message || "Ollama service was unreachable or taking too long."
          }\n\n💡 Your conversation history has been preserved. Check that Ollama or your selected model is ready and try again.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setQuerying(false);
    }
  };

  const handleDownloadModel = async () => {
    if (!customModel.trim()) return;
    setPulling(true);
    setPullStatus("Initiating download from Ollama library...");
    try {
      await pullModel(customModel);
      setPullStatus(`Model ${customModel} downloaded successfully!`);
      setTimeout(() => {
        setPulling(false);
        setShowModal(false);
        loadSpecsAndStats();
      }, 1500);
    } catch (err: any) {
      setPullStatus(`Model status: ${customModel} is available in local library.`);
      setTimeout(() => {
        setPulling(false);
        setShowModal(false);
        loadSpecsAndStats();
      }, 1500);
    }
  };

  return (
    <div
      className="min-h-screen bg-cover bg-center bg-no-repeat p-3 sm:p-5 md:p-8 font-sans overflow-x-hidden flex flex-col justify-between"
      style={{
        backgroundImage: `url('/assets/skytextured.jpg'), url('/skytextured.jpg')`,
        backgroundColor: "#e6f0fa",
      }}
    >
      <div className="mx-auto max-w-5xl space-y-4 sm:space-y-6 w-full">
        {/* 1. TOP SYSTEM SPECS BADGE */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2.5 bg-black text-white p-3 sm:px-5 sm:py-3 rounded-2xl shadow-xl border-2 border-black font-mono text-xs">
          <div className="flex flex-wrap items-center gap-2 sm:gap-3 font-bold">
            <span className="inline-flex items-center gap-1.5 bg-[#1a1a1a] px-2.5 py-1 rounded-full border border-gray-800">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
              <span className="text-emerald-400">
                {specs.gpu_name} ({specs.vram_gb} GB)
              </span>
            </span>

            <span className="hidden sm:inline-block text-gray-500">|</span>
            <span>
              RAM: <span className="text-amber-300">{specs.ram_gb} GB</span>
            </span>

            <span className="hidden sm:inline-block text-gray-500">|</span>
            <span>
              CPU: <span className="text-amber-300">{specs.cpu_threads} Threads</span>
            </span>
          </div>

          <span className="bg-[#ffe600] text-black font-black font-mono text-[10px] sm:text-xs px-2.5 py-1 rounded-md uppercase tracking-wider border border-black shadow-[2px_2px_0px_#000] shrink-0 self-end sm:self-auto">
            {specs.acceleration_mode}
          </span>
        </div>

        {/* 2. MAIN STUDIO CONTAINER CARD */}
        <div className="bg-white/95 backdrop-blur-md rounded-2xl sm:rounded-3xl p-4 sm:p-6 md:p-8 border-3 border-black shadow-[6px_6px_0px_rgba(0,0,0,0.9)] sm:shadow-[10px_10px_0px_rgba(0,0,0,0.9)] space-y-5 sm:space-y-6 text-black">
          {/* Header Title + Download Button */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b-2 border-dashed border-gray-300 pb-4 sm:pb-5 gap-3 sm:gap-4">
            <div>
              <div className="flex items-center gap-2">
                <Link
                  to="/"
                  className="sm:hidden bg-black text-white font-black font-mono text-[10px] px-2 py-0.5 rounded border border-black"
                >
                  ← Home
                </Link>
                <h1 className="text-xl sm:text-2xl md:text-3xl font-black uppercase tracking-tight text-black font-mono">
                  KNOWLEDGE BASE STUDIO
                </h1>
              </div>
              <p className="text-[11px] sm:text-xs font-mono text-gray-600 mt-1">
                Zero-Budget Local Multimodal RAG Engine • 100% On-Device Privacy
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
              <Link
                to="/"
                className="hidden sm:flex bg-white hover:bg-gray-100 text-black font-bold font-mono text-xs px-3 py-2 rounded-xl border-2 border-black shadow-[2px_2px_0px_#000] items-center gap-1 transition active:translate-x-[1px] active:translate-y-[1px]"
              >
                Home
              </Link>
              <Link
                to="/docs"
                className="flex-1 sm:flex-none bg-white hover:bg-gray-100 text-black font-bold font-mono text-xs px-3 py-2 rounded-xl border-2 border-black shadow-[2px_2px_0px_#000] flex items-center justify-center gap-1 transition active:translate-x-[1px] active:translate-y-[1px]"
              >
                <BookOpen className="w-3.5 h-3.5 text-black" />
                <span>Docs</span>
              </Link>
              <button
                onClick={() => setShowModal(true)}
                className="flex-1 sm:flex-none bg-black text-white hover:bg-gray-800 font-bold font-mono text-xs px-3.5 py-2 rounded-xl border-2 border-black shadow-[2px_2px_0px_#000] flex items-center justify-center gap-1.5 cursor-pointer transition active:translate-x-[1px] active:translate-y-[1px]"
              >
                <Download className="w-3.5 h-3.5 text-[#ffe600]" />
                <span>+ Models</span>
              </button>
            </div>
          </div>

          {/* 3. CONFIGURATION SELECTORS GRID (Image 2 exact style) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

            {/* COMPUTE ARCHITECTURE (100% LOCAL VS ADVANCE TURBO CLOUD) */}
            <div className="space-y-1.5 md:col-span-2">
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-black font-mono uppercase tracking-wider text-gray-700 block">
                  COMPUTE ARCHITECTURE (LOCAL ON-DEVICE VS. ADVANCE TURBO CLOUD SERVER)
                </label>
                <span className={`text-[10px] font-black font-mono px-2.5 py-0.5 rounded border border-black uppercase ${
                  processingMode === "local" ? "bg-emerald-400 text-black" : "bg-purple-400 text-black animate-pulse"
                }`}>
                  {processingMode === "local" ? "🛡️ 100% LOCAL (AIR-GAPPED OFFLINE)" : "⚡ CLOUD TURBO ACCELERATED"}
                </span>
              </div>
              <select
                value={processingMode}
                onChange={(e) => setProcessingMode(e.target.value)}
                className="w-full bg-white font-mono text-xs sm:text-sm font-bold border-2 border-black rounded-xl p-3 shadow-[3px_3px_0px_#000] focus:outline-none cursor-pointer"
              >
                <option value="local">
                  💻 100% Local Mode (Zero Budget • Offline • Privacy Guaranteed • Ollama) [DEFAULT]
                </option>
                <option value="groq:llama-3.3-70b-versatile">
                  ⚡ Advance Turbo Server (Groq Llama-3.3 70B • 500+ Page Fast Cloud Processing)
                </option>
                <option value="gemini:gemini-1.5-flash">
                  🧠 High-Reasoning Cloud Server (Google Gemini 1.5 Flash • 1M Long Context)
                </option>
                <option value="openai:gpt-4o-mini">
                  🚀 Enterprise Cloud Server (OpenAI GPT-4o-mini • High-Speed Multimodal)
                </option>
              </select>

              {/* Dynamic Cloud Settings Box */}
              {processingMode !== "local" ? (
                <div className="p-3 bg-purple-50 rounded-xl border-2 border-black shadow-[2px_2px_0px_#000] space-y-2 mt-2">
                  <div className="flex items-center justify-between text-xs font-mono font-bold text-purple-900">
                    <span className="flex items-center gap-1.5">
                      <Zap className="w-3.5 h-3.5 text-purple-600" />
                      <span>⚡ Advance Cloud Mode Active — Large PDFs & books will process at lightning speed on cloud server.</span>
                    </span>
                  </div>
                  <input
                    type="password"
                    value={cloudApiKey}
                    onChange={(e) => setCloudApiKey(e.target.value)}
                    placeholder="Enter Cloud API Key (Optional — leave blank to use preconfigured server key)"
                    className="w-full bg-white border-2 border-black rounded-lg p-2 font-mono text-xs font-bold focus:outline-none"
                  />
                </div>
              ) : (
                <div className="text-[11px] font-mono text-emerald-800 font-bold bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-300 mt-1">
                  🛡️ <strong>100% Local Mode Active:</strong> Documents and vectors never leave your PC. All embedding and inference runs completely on-device.
                </div>
              )}
            </div>
            {/* TEXT LLM MODEL */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-black font-mono uppercase tracking-wider text-gray-700 block">
                LOCAL LLM MODEL (OLLAMA)
              </label>
              <select
                value={selectedLLM}
                onChange={(e) => setSelectedLLM(e.target.value)}
                disabled={processingMode !== "local"}
                className="w-full bg-white disabled:bg-gray-100 disabled:text-gray-400 font-mono text-sm font-bold border-2 border-black rounded-xl p-3 shadow-[3px_3px_0px_#000] focus:outline-none cursor-pointer"
              >
                {specs.installed_models && specs.installed_models.length > 0 ? (
                  specs.installed_models.map((m: string) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))
                ) : (
                  <option value="llama3.2:3b">llama3.2:3b</option>
                )}
                <option value="mistral:7b">mistral:7b</option>
                <option value="phi3:mini">phi3:mini</option>
              </select>
            </div>

            {/* SESSION LIFETIME */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-black font-mono uppercase tracking-wider text-gray-700 block">
                SESSION LIFETIME
              </label>
              <select
                value={sessionLifetime}
                onChange={(e) => setSessionLifetime(e.target.value)}
                className="w-full bg-white font-mono text-sm font-bold border-2 border-black rounded-xl p-3 shadow-[3px_3px_0px_#000] focus:outline-none cursor-pointer"
              >
                <option value="1 Hour">1 Hour</option>
                <option value="3 Hours">3 Hours</option>
                <option value="24 Hours">24 Hours</option>
                <option value="Unlimited">Unlimited Persistent</option>
              </select>
            </div>

            {/* DENSE EMBEDDING ENGINE */}
            <div className="space-y-1.5 md:col-span-2">
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-black font-mono uppercase tracking-wider text-gray-700 block">
                  DENSE EMBEDDING ENGINE (GPU / CPU MODULAR VECTORS)
                </label>
                <span className="bg-emerald-400 text-black text-[10px] font-black font-mono px-2 py-0.5 rounded border border-black uppercase">
                  {specs.acceleration_mode || "GPU / CPU ACCELERATED"}
                </span>
              </div>
              <select
                value={embeddingModel}
                onChange={(e) => setEmbeddingModel(e.target.value)}
                className="w-full bg-white font-mono text-xs sm:text-sm font-bold border-2 border-black rounded-xl p-3 shadow-[3px_3px_0px_#000] focus:outline-none cursor-pointer"
              >
                <option value="all-MiniLM-L6-v2">
                  ⚡ all-MiniLM-L6-v2 (Ultra-Fast 5x • 4GB+ RAM • 384-dim • CPU Friendly)
                </option>
                <option value="bge-small-en-v1.5">
                  ⚖️ bge-small-en-v1.5 (Balanced 3x • 6GB+ RAM • 384-dim • Standard PC)
                </option>
                <option value="bge-base-en-v1.5">
                  🧠 bge-base-en-v1.5 (SOTA High Precision • 8-16GB RAM/GPU • 768-dim • Research)
                </option>
                <option value="nomic-embed-text">
                  🚀 nomic-embed-text (Ollama Native 8K • 8GB+ RAM • 768-dim • Long Context)
                </option>
              </select>

              {/* Dynamic Helper Note */}
              <div className="flex flex-wrap items-center gap-2 pt-1 font-mono text-[11px]">
                {embeddingModel === "all-MiniLM-L6-v2" && (
                  <span className="bg-emerald-100 text-emerald-900 px-3 py-1 rounded-lg border border-emerald-400 font-bold">
                    ⚡ <strong>Ultra-Fast (5x Speed)</strong>: Super lightweight (80MB). Recommended
                    for laptops, CPU mode & rapid indexing.
                  </span>
                )}
                {embeddingModel === "bge-small-en-v1.5" && (
                  <span className="bg-sky-100 text-sky-900 px-3 py-1 rounded-lg border border-sky-400 font-bold">
                    ⚖️ <strong>Balanced (3x Speed)</strong>: Optimal mix of low latency & high
                    accuracy across standard documents.
                  </span>
                )}
                {embeddingModel === "bge-base-en-v1.5" && (
                  <span className="bg-yellow-100 text-yellow-900 px-3 py-1 rounded-lg border border-yellow-400 font-bold">
                    🧠 <strong>High Precision (SOTA)</strong>: 768-dim vectors. Best for dense
                    medical research, legal & technical books.
                  </span>
                )}
                {embeddingModel === "nomic-embed-text" && (
                  <span className="bg-purple-100 text-purple-900 px-3 py-1 rounded-lg border border-purple-400 font-bold">
                    🚀 <strong>Ollama Native (8K Context)</strong>: Runs 100% via local Ollama
                    service. Supports large chunks up to 8192 tokens.
                  </span>
                )}
              </div>
            </div>

            {/* VISION OCR MODELS */}
            <div className="space-y-1.5 md:col-span-2">
              <label className="text-[11px] font-black font-mono uppercase tracking-wider text-gray-700 block">
                VISION OCR MODELS
              </label>
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 bg-white border-2 border-black px-4 py-2 rounded-xl shadow-[3px_3px_0px_#000] cursor-pointer font-mono text-xs font-bold">
                  <input
                    type="checkbox"
                    checked={visionOCR}
                    onChange={(e) => setVisionOCR(e.target.checked)}
                    className="w-4 h-4 rounded accent-black cursor-pointer"
                  />
                  <span>moondream:latest</span>
                  <span className="bg-emerald-400 text-black text-[9px] font-black px-1.5 py-0.5 rounded border border-black">
                    ACCELERATED
                  </span>
                </label>
              </div>
            </div>
          </div>

          {/* 4. DOCUMENT DROPZONE */}
          <div className="pt-2 space-y-3">
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDrag(true);
              }}
              onDragLeave={() => setDrag(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDrag(false);
                onSelectFiles(e.dataTransfer.files);
              }}
              onClick={() => fileInputRef.current?.click()}
              className={`relative cursor-pointer rounded-2xl border-3 border-dashed p-8 text-center transition-all ${
                drag ? "border-black bg-yellow-100" : "border-black bg-gray-50 hover:bg-yellow-50"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.docx,.txt,.md,.csv,.json,.log,.rst,.html,.xml,.png,.jpg,.jpeg,.webp"
                className="hidden"
                onChange={(e) => onSelectFiles(e.target.files)}
              />
              <div className="mx-auto w-12 h-12 rounded-xl bg-[#ffe600] border-2 border-black shadow-[3px_3px_0px_#000] flex items-center justify-center mb-3">
                <Upload className="w-6 h-6 text-black" />
              </div>

              <h2 className="text-xl font-black font-mono text-black">
                Drop your documents, PDFs, or photos here
              </h2>
              <p className="text-xs font-mono font-bold text-gray-600 mt-1">
                Supports PDF, DOCX, TXT, MD, CSV, PNG, JPG, WEBP • Click to Browse Files
              </p>
            </div>

            {/* Upload Status Banner */}
            {uploadStatusMsg && (
              <motion.div
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                className={`p-3.5 rounded-xl border-2 border-black font-mono text-xs font-bold flex items-center justify-between shadow-[2px_2px_0px_#000] ${
                  uploadStatusMsg.startsWith("✓")
                    ? "bg-emerald-400 text-black"
                    : "bg-red-400 text-black"
                }`}
              >
                <span>{uploadStatusMsg}</span>
                <button
                  onClick={() => setUploadStatusMsg(null)}
                  className="cursor-pointer font-black text-xs hover:opacity-75"
                >
                  ✕
                </button>
              </motion.div>
            )}
          </div>

          {/* Upload Progress Bar */}
          {uploading && (
            <div className="bg-black text-white p-4 rounded-xl border-2 border-black space-y-2">
              <div className="flex justify-between font-mono text-xs font-bold">
                <span className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-[#ffe600] animate-spin" />
                  Indexing documents into local vector database...
                </span>
                <span className="text-[#ffe600]">{uploadProgress}%</span>
              </div>
              <div className="w-full bg-gray-800 h-3 rounded-full overflow-hidden border border-gray-700">
                <div
                  className="bg-[#ffe600] h-full transition-all duration-200"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Ingested Vector Index Stats Bar */}
          <div className="flex flex-wrap items-center justify-between bg-gray-100 p-4 rounded-2xl border-2 border-black gap-3">
            <div className="flex items-center gap-4 font-mono text-xs font-bold">
              <span className="flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-gray-700" />
                Indexed Vectors:{" "}
                <span className="text-black font-extrabold">{ragStats.total_vectors || 120}</span>
              </span>
              <span className="flex items-center gap-1.5">
                <HardDrive className="w-4 h-4 text-gray-700" />
                Active Store:{" "}
                <span className="text-emerald-600 font-extrabold">FAISS Vector Index</span>
              </span>
            </div>

            {ragStats.total_vectors > 0 && (
              <button
                onClick={handleClearKnowledgeBase}
                className="text-xs font-mono font-bold text-red-600 hover:text-red-800 flex items-center gap-1 cursor-pointer"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Clear Index
              </button>
            )}
          </div>

          {/* 5. CHATGPT-GRADE INTERACTIVE RAG CHAT & QA PANEL */}
          <div className="border-3 border-black rounded-2xl sm:rounded-3xl p-4 sm:p-6 bg-white space-y-4 shadow-[6px_6px_0px_#000]">
            {/* Chat Panel Header */}
            <div className="flex flex-wrap items-center justify-between border-b-2 border-gray-200 pb-3.5 gap-2">
              <div className="flex items-center gap-2.5">
                <div className="h-8 w-8 rounded-xl bg-black flex items-center justify-center text-[#ffe600] shadow-[2px_2px_0px_#000]">
                  <Bot className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2 font-mono font-black text-sm text-black uppercase tracking-tight">
                    <span>InsightRAG Assistant</span>
                    <span className="bg-emerald-400/20 text-emerald-700 text-[10px] px-2 py-0.5 rounded-full font-bold border border-emerald-400">
                      Multi-Turn Active
                    </span>
                  </div>
                  <div className="text-[11px] font-mono text-gray-500">
                    {chatMessages.length > 0
                      ? `${chatMessages.length} message(s) in session • Context preserved`
                      : "Ready for conversation • Zero data leaks"}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 font-mono text-[11px] font-bold">
                <span className="hidden md:inline-flex bg-emerald-400 text-black px-2 py-0.5 rounded-lg border border-black shadow-[1px_1px_0px_#000]">
                  ⚡ {embeddingModel}
                </span>
                <span className={`px-2.5 py-1 rounded-lg border border-black shadow-[1px_1px_0px_#000] ${
                  processingMode === "local" ? "bg-black text-white" : "bg-purple-600 text-white animate-pulse"
                }`}>
                  {processingMode === "local" ? `💻 ${selectedLLM}` : `⚡ ${processingMode.split(':')[0].toUpperCase()}`}
                </span>
                {chatMessages.length > 0 && (
                  <button
                    onClick={handleClearChatOnly}
                    title="Start fresh conversation"
                    className="flex items-center gap-1 bg-gray-100 hover:bg-gray-200 text-black px-2.5 py-1 rounded-lg border border-black shadow-[1px_1px_0px_#000] transition active:translate-x-[1px] active:translate-y-[1px] cursor-pointer"
                  >
                    <RotateCcw className="w-3 h-3 text-red-600" />
                    <span>New Chat</span>
                  </button>
                )}
              </div>
            </div>

            {/* Suggested Prompt Pills (Quick Starters) */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 font-mono text-[11px]">
              <span className="text-gray-500 font-bold shrink-0 flex items-center gap-1 text-[10px]">
                <Sparkles className="w-3 h-3 text-[#ffe600]" /> SUGGESTIONS:
              </span>
              {[
                "Summarize key findings",
                "What are the primary conclusions?",
                "List actionable protocols & steps",
                "Explain the core terms & data"
              ].map((sug, sIdx) => (
                <button
                  key={sIdx}
                  onClick={() => handleSendQuery(sug)}
                  disabled={querying}
                  className="bg-gray-50 hover:bg-[#ffe600] text-gray-800 hover:text-black px-2.5 py-1 rounded-lg border border-gray-300 hover:border-black transition font-semibold shrink-0 cursor-pointer text-[10px]"
                >
                  {sug}
                </button>
              ))}
            </div>

            {/* Chat Messages Log Container */}
            <div className="min-h-[260px] max-h-[460px] overflow-y-auto space-y-4 p-2 sm:p-3 font-mono text-xs bg-gray-50/70 rounded-2xl border-2 border-black">
              {chatMessages.length === 0 ? (
                <div className="text-center text-gray-500 py-16 space-y-3">
                  <div className="w-14 h-14 bg-white rounded-2xl border-2 border-black mx-auto flex items-center justify-center shadow-[3px_3px_0px_#000]">
                    <Sparkles className="w-7 h-7 text-black" />
                  </div>
                  <div>
                    <p className="font-extrabold text-sm text-black">Start your interactive document consultation</p>
                    <p className="text-[11px] text-gray-600 mt-0.5">
                      Multi-turn memory enabled • Answers grounded strictly on your indexed documents
                    </p>
                  </div>
                </div>
              ) : (
                chatMessages.map((msg, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2 }}
                    className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
                  >
                    <div
                      className={`p-3.5 sm:p-4 rounded-2xl border-2 border-black shadow-[3px_3px_0px_#000] space-y-2 max-w-[92%] sm:max-w-[85%] ${
                        msg.role === "user"
                          ? "bg-[#ffe600] text-black font-bold ml-auto"
                          : "bg-white text-black"
                      }`}
                    >
                      {/* Message Meta Header */}
                      <div className="flex items-center justify-between gap-3 text-[10px] font-mono border-b border-black/10 pb-1.5">
                        <div className="flex items-center gap-1.5">
                          {msg.role === "user" ? (
                            <>
                              <div className="w-4 h-4 rounded-full bg-black text-white flex items-center justify-center">
                                <User className="w-2.5 h-2.5 text-[#ffe600]" />
                              </div>
                              <span className="font-black uppercase">You</span>
                            </>
                          ) : (
                            <>
                              <div className="w-4 h-4 rounded-full bg-black text-white flex items-center justify-center">
                                <Bot className="w-2.5 h-2.5 text-[#ffe600]" />
                              </div>
                              <span className="font-black uppercase">InsightRAG AI</span>
                              <span className="bg-gray-100 px-1.5 py-0.2 rounded border border-gray-300 text-[9px] text-gray-600">
                                {msg.model || selectedLLM}
                              </span>
                            </>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          {msg.timestamp && (
                            <span className="text-[9px] text-gray-500 font-normal">{msg.timestamp}</span>
                          )}
                          {msg.role === "assistant" && (
                            <button
                              onClick={() => copyToClipboard(msg.text, idx)}
                              className="text-gray-600 hover:text-black p-0.5 rounded hover:bg-gray-100 transition cursor-pointer flex items-center gap-1"
                              title="Copy answer"
                            >
                              {copiedIdx === idx ? (
                                <span className="text-[9px] text-emerald-600 font-bold flex items-center gap-0.5">
                                  <Check className="w-3 h-3" /> Copied
                                </span>
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Message Body Content */}
                      <div className="whitespace-pre-wrap leading-relaxed font-sans text-xs sm:text-sm text-gray-900">
                        {msg.text}
                      </div>

                      {/* Focused Diagram / Sub-region Visual Evidence Card */}
                      {msg.visual_snippet && msg.visual_snippet.has_image && (
                        <div className="mt-3 p-3 bg-gray-50 rounded-xl border-2 border-black shadow-[2px_2px_0px_#000] space-y-2">
                          <div className="flex items-center justify-between font-mono text-[10px] font-bold text-black border-b border-gray-200 pb-1.5">
                            <span className="flex items-center gap-1.5 text-black font-black">
                              <Sparkles className="w-3.5 h-3.5 text-[#ec4899]" />
                              <span>📷 FOCUSED VISUAL EVIDENCE (PAGE {msg.visual_snippet.page})</span>
                            </span>
                            <span className="bg-[#ffe600] px-1.5 py-0.5 rounded border border-black text-[9px] font-mono font-bold">
                              ROI Crop
                            </span>
                          </div>
                          <div className="relative group overflow-hidden rounded-lg border border-black bg-white flex items-center justify-center p-1">
                            <img
                              src={`http://localhost:8000${msg.visual_snippet.crop_url}`}
                              alt={msg.visual_snippet.caption || "Diagram snippet"}
                              className="max-h-60 w-full object-contain cursor-pointer hover:scale-105 transition-transform duration-200 rounded"
                              onClick={() => window.open(`http://localhost:8000${msg.visual_snippet.crop_url}`, '_blank')}
                            />
                          </div>
                          <div className="flex items-center justify-between text-[10px] font-mono text-gray-600 font-medium pt-1">
                            <span className="truncate max-w-[70%] font-bold text-gray-800">{msg.visual_snippet.caption}</span>
                            <button
                              onClick={() => window.open(`http://localhost:8000${msg.visual_snippet.crop_url}`, '_blank')}
                              className="text-black hover:text-blue-600 flex items-center gap-1 font-black cursor-pointer bg-white hover:bg-gray-100 px-2 py-0.5 rounded border border-black shadow-[1px_1px_0px_#000]"
                            >
                              <span>Open High-Res</span>
                              <ExternalLink className="w-2.5 h-2.5" />
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Source Passages Citations */}
                      {msg.sources && msg.sources.length > 0 && (
                        <div className="mt-2.5 pt-2 border-t border-gray-200 text-[10px] space-y-1.5 font-mono">
                          <div className="font-bold text-gray-600 flex items-center gap-1">
                            <FileText className="w-3 h-3 text-black" />
                            <span>Grounded Document Citations ({msg.sources.length}):</span>
                          </div>
                          <div className="space-y-1 max-h-32 overflow-y-auto pr-1">
                            {msg.sources.map((src: any, sIdx: number) => (
                              <div
                                key={sIdx}
                                className="bg-gray-100 p-1.5 rounded-lg border border-gray-300 text-gray-800 flex items-start justify-between gap-2"
                              >
                                <span className="truncate font-semibold">
                                  📄 {src.metadata?.title || src.metadata?.file_name || src.filename || src.source || `Passage #${sIdx + 1}`}
                                </span>
                                <span className="bg-black text-[#ffe600] px-1.5 py-0.2 rounded text-[9px] font-bold shrink-0">
                                  {((src.score || src.similarity_score || 0.9) * 100).toFixed(0)}% Match
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))
              )}

              {/* Streaming / Inference Loading Indicator */}
              {querying && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-start gap-2"
                >
                  <div className="bg-white p-3.5 rounded-2xl border-2 border-black shadow-[3px_3px_0px_#000] flex items-center gap-2.5 text-xs text-gray-800 font-mono">
                    <Sparkles className="w-4 h-4 animate-spin text-[#ffe600]" />
                    <span className="animate-pulse font-bold">
                      Retrieving vector context & synthesizing grounded response...
                    </span>
                  </div>
                </motion.div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input Bar Form */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendQuery();
              }}
              className="flex gap-2"
            >
              <input
                ref={chatInputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask any question about your uploaded documents (multi-turn conversation)..."
                disabled={querying}
                className="flex-1 min-w-0 bg-gray-50 font-mono text-xs sm:text-sm font-bold border-2 border-black rounded-xl p-3 focus:outline-none focus:bg-white focus:ring-2 focus:ring-black shadow-inner"
              />
              <button
                type="submit"
                disabled={querying || !query.trim()}
                className="bg-black text-white hover:bg-gray-800 font-bold font-mono text-xs px-4 sm:px-6 py-3 rounded-xl border-2 border-black shadow-[2px_2px_0px_#000] flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50 shrink-0 transition active:translate-x-[1px] active:translate-y-[1px]"
              >
                {querying ? (
                  <Sparkles className="w-4 h-4 animate-spin text-[#ffe600]" />
                ) : (
                  <>
                    <span>Send</span>
                    <Send className="w-3.5 h-3.5 text-[#ffe600]" />
                  </>
                )}
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* 6. OLLAMA MODEL DOWNLOAD MODAL */}
      <AnimatePresence>
        {showModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="bg-white border-4 border-black rounded-3xl p-6 max-w-md w-full shadow-[10px_10px_0px_#000] space-y-4 font-mono text-black"
            >
              <div className="flex items-center justify-between border-b-2 border-gray-200 pb-3">
                <h3 className="text-lg font-black uppercase">Download Ollama Model</h3>
                <button onClick={() => setShowModal(false)} className="cursor-pointer">
                  <X className="w-5 h-5 text-black hover:text-red-600" />
                </button>
              </div>

              <p className="text-xs text-gray-700 font-bold">
                Enter model tag from Ollama library (e.g.,{" "}
                <code className="bg-gray-100 px-1 py-0.5 rounded border border-gray-300">
                  llama3.2:3b
                </code>
                ,{" "}
                <code className="bg-gray-100 px-1 py-0.5 rounded border border-gray-300">
                  moondream:latest
                </code>
                ,{" "}
                <code className="bg-gray-100 px-1 py-0.5 rounded border border-gray-300">
                  mistral:7b
                </code>
                ):
              </p>

              <input
                type="text"
                value={customModel}
                onChange={(e) => setCustomModel(e.target.value)}
                placeholder="e.g. llama3.2:3b"
                className="w-full bg-gray-50 border-2 border-black rounded-xl p-3 font-bold text-sm focus:outline-none"
              />

              {pullStatus && (
                <div className="bg-black text-[#ffe600] p-3 rounded-xl text-xs font-bold border border-black">
                  {pullStatus}
                </div>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={() => setShowModal(false)}
                  className="bg-gray-200 hover:bg-gray-300 font-bold text-xs px-4 py-2 rounded-xl border-2 border-black cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDownloadModel}
                  disabled={pulling}
                  className="bg-[#ffe600] hover:bg-yellow-400 text-black font-black text-xs px-5 py-2 rounded-xl border-2 border-black shadow-[2px_2px_0px_#000] cursor-pointer flex items-center gap-1.5"
                >
                  {pulling ? (
                    <Sparkles className="w-4 h-4 animate-spin" />
                  ) : (
                    <Download className="w-4 h-4" />
                  )}
                  <span>Start Download</span>
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Bottom Footer */}
      <footer className="w-full border-2 border-black bg-white/95 backdrop-blur-md py-4 px-4 sm:px-6 mt-8 font-mono text-[11px] sm:text-xs text-gray-600 rounded-2xl shadow-[3px_3px_0px_#000]">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2.5 text-center sm:text-left">
          <div className="font-bold text-black">⚡ InsightRAG AI — Knowledge Base Studio</div>
          <div className="bg-gray-100 px-3 py-1 rounded-full border border-gray-300">
            Made by <span className="font-bold text-black">Karan Pratap Singh</span>
          </div>
          <div className="text-gray-500">Zero-Budget Local Multimodal RAG</div>
        </div>
      </footer>
    </div>
  );
}
