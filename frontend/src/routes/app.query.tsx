import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Search,
  Sparkles,
  FileText,
  CheckCircle2,
  Upload,
  Cpu,
  Bot,
  Database,
  Layers,
  AlertCircle,
  FileCheck2,
} from "lucide-react";
import { PageHeader } from "@/components/dashboard/DashboardShell";
import { queryRAG, getRAGStats } from "../services/api";

export const Route = createFileRoute("/app/query")({
  head: () => ({ meta: [{ title: "RAG Document Intelligence & Ollama Q&A — InsightForge AI" }] }),
  component: QueryPage,
});

const LOCAL_MODEL = "llama3.2:3b";
const LOCAL_MODEL_LABEL = "Llama 3.2 3B — Local Ollama Engine";

const samplePrompts = [
  "Summarize the key medical or research points of the document",
  "What are the primary findings and statistical conclusions?",
  "List any clinical protocols, guidelines, or action items",
  "Explain the core terms and concepts described in the text",
];

interface IndexedFile {
  name: string;
  size_bytes: number;
  extension: string;
}

export function QueryPage() {
  const [q, setQ] = useState("");
  const selectedModel = LOCAL_MODEL;
  const [submitted, setSubmitted] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [aiAnswer, setAiAnswer] = useState<string | null>(null);
  const [usedLlm, setUsedLlm] = useState<boolean>(false);
  const [activeModel, setActiveModel] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  // Document Knowledge Base State
  const [indexedFiles, setIndexedFiles] = useState<IndexedFile[]>([]);
  const [totalVectors, setTotalVectors] = useState<number>(0);

  const loadStats = async () => {
    try {
      const stats = await getRAGStats();
      if (stats) {
        setTotalVectors(stats.total_vectors || 0);
        if (stats.files && Array.isArray(stats.files)) {
          setIndexedFiles(stats.files);
        }
      }
    } catch (err) {
      console.log("Could not load stats yet", err);
    }
  };

  useEffect(() => {
    loadStats();

    // Check if prompt parameter was passed from Anomaly Console or Upload Page
    const params = new URLSearchParams(window.location.search);
    const initialPrompt = params.get("prompt");
    if (initialPrompt) {
      setQ(initialPrompt);
      handleSearch(initialPrompt);
    }
  }, []);

  const handleSearch = async (queryText: string) => {
    if (!queryText || !queryText.trim()) return;
    const cleanQ = queryText.trim();
    setSubmitted(cleanQ);
    setHasSearched(true);
    setLoading(true);
    setAiAnswer(null);
    setUsedLlm(false);

    try {
      const res = await queryRAG(cleanQ, 5, 0.0, LOCAL_MODEL);

      if (res) {
        if (res.answer) {
          setAiAnswer(res.answer);
          setUsedLlm(res.used_llm || false);
          setActiveModel(res.llm_model || selectedModel);
        }

        if (res.results && res.results.length > 0) {
          const mapped = res.results.map((r: any, idx: number) => {
            const meta = r.metadata || {};
            const docName = meta.title || meta.file_name || meta.source || r.document_id || `Document #${idx + 1}`;
            return {
              id: r.chunk_id || `chunk_${idx}`,
              title: docName,
              snippet: r.text || "",
              score: typeof r.score === "number" ? r.score : 0.85,
              source: meta.source || meta.file_name || `Vector Passage [${idx + 1}]`,
              tokenCount: meta.token_count,
            };
          });
          setResults(mapped);
        } else {
          setResults([]);
          if (!res.answer) {
            setAiAnswer("No relevant excerpts found in your uploaded documents for this query. Upload more documents to expand your knowledge base.");
          }
        }
      } else {
        setResults([]);
        setAiAnswer("No response received from RAG service.");
      }
    } catch (err: any) {
      console.error("Query failed:", err);
      setResults([]);
      setAiAnswer("Query failed. Please ensure the backend server is running and files are uploaded.");
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <>
      <PageHeader
        title="RAG Document Query & Synthesis (Waypoint Module)"
        description="Ask any question against your vector database. Synthesizes grounded responses with local Ollama Llama 3.2 models."
      />

      <div className="p-6 md:p-8 space-y-6 bg-[#000000] min-h-screen text-white">
        <div className="mx-auto max-w-4xl space-y-6">

          {/* Module Identity Chip */}
          <div className="flex items-center justify-between">
            <div className="eyebrow-hashicorp text-[#00bcff] flex items-center gap-2">
              <Search className="w-4 h-4 text-[#00bcff]" />
              <span>WAYPOINT LOCAL OLLAMA SEARCH ENGINE</span>
            </div>
            <span className="product-pill font-mono text-xs text-[#00bcff] border-[#00bcff]/30">
              Offline Llama 3.2 3B
            </span>
          </div>

          {/* 1. KNOWLEDGE BASE STATUS BAR (Strictly Query Focus - Link to Upload) */}
          <div className="hashicorp-card p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-[#00bcff]/30">
            <div className="flex items-center gap-3">
              <Database className="h-5 w-5 text-[#00bcff]" />
              <div>
                <div className="headline-hashicorp text-white text-sm flex items-center gap-2">
                  <span>Vector Knowledge Base</span>
                  <span className="bg-[#00bcff]/20 text-[#00bcff] font-mono text-xs px-2.5 py-0.5 rounded-full font-bold">
                    {totalVectors} Vector Chunks
                  </span>
                </div>
                <div className="body-hashicorp text-xs text-[#b2b6bd] mt-0.5">
                  {indexedFiles.length > 0
                    ? `Currently querying across ${indexedFiles.length} indexed document(s).`
                    : "No documents indexed yet. Upload documents in Document Ingestion to query."}
                </div>
              </div>
            </div>

            <Link to="/app/upload">
              <button className="btn-hashicorp-secondary flex items-center gap-2 text-xs py-2 px-3">
                <Upload className="w-3.5 h-3.5 text-[#00bcff]" />
                <span>+ Upload More Files</span>
              </button>
            </Link>
          </div>

          {/* LIST OF INDEXED FILES SUMMARY CHIPS */}
          {indexedFiles.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="eyebrow-hashicorp text-[10px] text-[#b2b6bd]">INDEXED FILES:</span>
              {indexedFiles.map((file, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#242424] border border-[rgba(178,182,189,0.12)] text-xs text-white font-mono"
                >
                  <FileCheck2 className="h-3.5 w-3.5 text-[#00bcff]" />
                  <span className="truncate max-w-[200px]">{file.name}</span>
                  <span className="text-[10px] text-[#b2b6bd]">({formatFileSize(file.size_bytes)})</span>
                </div>
              ))}
            </div>
          )}

          {/* 2. LOCAL OLLAMA MODEL BADGE */}
          <div className="hashicorp-card p-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bot className="h-4 w-4 text-[#00bcff]" />
              <span className="eyebrow-hashicorp text-[#00bcff]">SYNTHESIS ENGINE:</span>
            </div>
            <span className="product-pill font-mono text-xs text-white border-[#00bcff]/40">
              <Cpu className="h-3 w-3 mr-1 inline text-[#00bcff]" />
              {LOCAL_MODEL_LABEL}
            </span>
          </div>

          {/* 3. QUERY INPUT & SEARCH FORM */}
          <div className="hashicorp-card p-6 space-y-4">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSearch(q);
              }}
              className="flex flex-col gap-4 md:flex-row md:items-center"
            >
              <div className="relative flex-1 flex items-center">
                <Search className="absolute left-4 h-5 w-5 text-[#b2b6bd]" />
                <input
                  type="text"
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Ask any question about your uploaded documents..."
                  className="w-full rounded-md border border-[rgba(178,182,189,0.2)] bg-[#000000] pl-12 pr-4 py-3 text-base text-white placeholder:text-[#b2b6bd] outline-none focus:border-[#00bcff]"
                />
              </div>
              <button
                type="submit"
                disabled={loading || !q.trim()}
                className="btn-product-waypoint flex items-center gap-2 justify-center shrink-0"
              >
                <Sparkles className="h-4 w-4 text-black" />
                <span>Search & Synthesize</span>
              </button>
            </form>

            {/* SAMPLE PROMPTS */}
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <span className="eyebrow-hashicorp text-[#b2b6bd] text-[10px] mr-1">SUGGESTIONS:</span>
              {samplePrompts.map((p, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setQ(p);
                    handleSearch(p);
                  }}
                  className="text-xs px-3 py-1 rounded-md border border-[rgba(178,182,189,0.2)] bg-[#242424] text-[#b2b6bd] hover:border-[#00bcff] hover:text-white transition cursor-pointer"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {/* 4. RESULTS SECTION */}
          {submitted && (
            <div className="eyebrow-hashicorp text-[#b2b6bd] flex items-center justify-between">
              <span>QUERY: <span className="text-white font-semibold">"{submitted}"</span></span>
              <span className="font-mono text-xs text-[#00bcff]">MODEL: {selectedModel}</span>
            </div>
          )}

          {loading ? (
            <div className="p-12 text-center text-[#b2b6bd] font-mono animate-pulse space-y-3 bg-[#141414] rounded-md border border-[rgba(178,182,189,0.2)]">
              <Sparkles className="h-7 w-7 text-[#00bcff] mx-auto animate-spin" />
              <div className="text-sm text-white">Searching vector index & synthesizing response via Ollama...</div>
              <div className="text-xs text-[#b2b6bd]">Retrieving cosine similarity matches from your files</div>
            </div>
          ) : (
            <div className="space-y-6">

              {/* AI SYNTHESIZED ANSWER */}
              {aiAnswer && (
                <motion.div
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  <div className="hashicorp-card p-6 border-[#00bcff]/40 space-y-4">
                    <div className="flex items-center justify-between border-b border-[rgba(178,182,189,0.12)] pb-3">
                      <div className="flex items-center gap-2">
                        <Bot className="h-5 w-5 text-[#00bcff]" />
                        <span className="headline-hashicorp text-white text-base">AI Synthesized Answer</span>
                      </div>
                      <span className="product-pill font-mono text-xs text-[#00bcff]">
                        <Cpu className="h-3 w-3 mr-1 inline" /> {activeModel || selectedModel}
                      </span>
                    </div>

                    <div className="body-hashicorp text-[#f4f4f5] leading-relaxed whitespace-pre-line font-sans">
                      {aiAnswer}
                    </div>

                    <div className="pt-2 flex items-center justify-between text-xs text-[#b2b6bd] border-t border-[rgba(178,182,189,0.12)]">
                      <span>Grounded strictly on retrieved context</span>
                      <span className="text-[11px] font-mono text-[#00bcff]">
                        {usedLlm ? "✓ Live Ollama Inference" : "FAISS Context Fallback"}
                      </span>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* RETRIEVED VECTOR PASSAGES (EXACT CITATIONS FROM UPLOADED FILES) */}
              {results.length > 0 && (
                <div className="space-y-4">
                  <div className="eyebrow-hashicorp text-[#00bcff] flex items-center gap-2">
                    <Layers className="h-4 w-4 text-[#00bcff]" />
                    <span>EXACT DOCUMENT CITATIONS ({results.length} MATCHES)</span>
                  </div>

                  {results.map((r, i) => (
                    <motion.div
                      key={r.id || i}
                      initial={{ opacity: 0, y: 15 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: i * 0.08 }}
                    >
                      <div className="hashicorp-card p-6 space-y-3">
                        <div className="flex items-center justify-between border-b border-[rgba(178,182,189,0.12)] pb-3">
                          <div className="flex items-center gap-2 truncate pr-2">
                            <FileText className="h-4 w-4 text-[#00bcff] shrink-0" />
                            <span className="headline-hashicorp text-white text-sm truncate">{r.title}</span>
                          </div>
                          <span className="bg-[#00bcff]/20 text-[#00bcff] font-mono text-xs px-2.5 py-0.5 rounded-full font-bold">
                            <CheckCircle2 className="h-3 w-3 mr-1 inline" /> {(r.score * 100).toFixed(1)}% Match
                          </span>
                        </div>

                        <p className="body-hashicorp text-sm text-white leading-relaxed font-sans whitespace-pre-line bg-[#242424] p-3 rounded-md border border-[rgba(178,182,189,0.12)]">
                          "{r.snippet}"
                        </p>

                        <div className="pt-2 flex items-center justify-between text-xs text-[#b2b6bd] border-t border-[rgba(178,182,189,0.12)]">
                          <span className="font-mono text-[11px] truncate max-w-md">{r.source}</span>
                          <span className="text-[11px] font-semibold text-[#00bcff] shrink-0">
                            FAISS Vector Chunk #{i + 1}
                          </span>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}

              {/* EMPTY SEARCH STATE */}
              {hasSearched && results.length === 0 && !aiAnswer && (
                <div className="p-12 text-center text-[#b2b6bd] bg-[#141414] rounded-md border border-[rgba(178,182,189,0.2)] space-y-3">
                  <AlertCircle className="h-8 w-8 text-[#b2b6bd] mx-auto opacity-70" />
                  <div className="headline-hashicorp text-white">No Matching Context Found</div>
                  <p className="body-hashicorp text-xs max-w-md mx-auto">
                    Try refining your query or upload more documents to your knowledge base in Document Ingestion.
                  </p>
                </div>
              )}

            </div>
          )}

        </div>
      </div>
    </>
  );
}