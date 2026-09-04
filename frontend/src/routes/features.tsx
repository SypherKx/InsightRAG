import { createFileRoute, Link } from "@tanstack/react-router";
import { Database, GitBranch, Brain, ArrowRight, Check, Download, ShieldCheck, Cpu } from "lucide-react";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";

export const Route = createFileRoute("/features")({
  head: () => ({
    meta: [
      { title: "Capabilities — InsightForge Healthcare & Education RAG" },
      {
        name: "description",
        content:
          "Cited RAG document search and local Llama 3.2 synthesis for medical & academic teams.",
      },
    ],
  }),
  component: FeaturesPage,
});

const capabilities = [
  {
    id: "rag",
    icon: Brain,
    product: "WAYPOINT RAG ENGINE",
    eyebrow: "RETRIEVAL-AUGMENTED GENERATION",
    title: "Ground-Truth Local RAG Search for Medical PDFs & Syllabi",
    body: "Indexes PubMed studies, FDA drug labels, hospital EMR records, and university textbooks into 100% local FAISS vector spaces for cited zero-hallucination answers.",
    bullets: [
      "FAISS dense vector index search across medical PDFs & lecture decks",
      "Page, paragraph, and table evidence citations",
      "Grounded prompt synthesis using local Ollama Llama 3.2 3B",
      "100% local index disk persistence for data privacy",
    ],
    metric: "384-D FAISS Vectors",
    status: "Active Engine",
  },
  {
    id: "ingestion",
    icon: Database,
    product: "TERRAFORM VECTOR STORE",
    eyebrow: "HIPAA & FERPA READY PIPELINE",
    title: "Schema-Aware Ingestion for Medical Records & Academic Docs",
    body: "Upload EMR CSV files, lab results, PubMed PDFs, or lecture slide decks. Local vector embeddings generate automatically.",
    bullets: [
      "Automatic schema detection for patient lab CSVs & medical records",
      "PDF text chunking windowing for research papers & textbooks",
      "Outlier-resilient numeric cleaning for clinical trial datasets",
      "100% offline local processing on your PC",
    ],
    metric: "Auto Schema Infer",
    status: "PDF Chunk Windowing",
  },
  {
    id: "attribution",
    icon: GitBranch,
    product: "NOMAD PRIVACY BLUEPRINT",
    eyebrow: "ZERO CLOUD TRANSMISSION",
    title: "100% Offline PC Hardware Execution",
    body: "Runs 100% offline using your computer's own RAM and CPU/GPU power. Zero cloud API calls or external server data leaks.",
    bullets: [
      "Zero external cloud API transmission",
      "Local disk persistence for encrypted vector indices",
      "Air-gapped clinical trial & academic document security",
      "Direct desktop execution with zero setup hassle",
    ],
    metric: "100% Local Power",
    status: "Air-Gapped Privacy",
  },
];

function FeaturesPage() {
  return (
    <MarketingLayout>
      {/* PAGE HEADER HERO */}
      <section className="bg-[#000000] py-14 md:py-20 border-b border-[rgba(178,182,189,0.12)] text-white">
        <div className="mx-auto max-w-4xl px-6 text-center space-y-4">
          <div className="eyebrow-hashicorp text-[#844fba] inline-block px-3 py-1 bg-[#844fba]/10 rounded-full border border-[#844fba]/20">
            HEALTHCARE & EDUCATION CAPABILITIES
          </div>
          <h1 className="display-hashicorp-lg text-white">
            Engineered for medical precision & academic clarity.
          </h1>
          <p className="body-hashicorp-lg text-[#b2b6bd] max-w-2xl mx-auto">
            Specialized modules built to accelerate medical research, assist clinical decision-making, and streamline academic document search on your PC.
          </p>
        </div>
      </section>

      {/* DETAILED MODULE SECTIONS */}
      <section className="bg-[#000000] py-16 md:py-24 border-b border-[rgba(178,182,189,0.12)] text-white">
        <div className="mx-auto max-w-6xl px-8 flex flex-col gap-16">
          {capabilities.map((c, i) => {
            const Icon = c.icon;
            const isReverse = i % 2 === 1;

            return (
              <div
                key={c.title}
                className={`grid gap-10 items-center lg:grid-cols-12 ${
                  isReverse ? "lg:[&>*:first-child]:order-2" : ""
                }`}
              >
                {/* Text Content */}
                <div className="lg:col-span-7 space-y-4">
                  <div className="eyebrow-hashicorp text-[#00bcff]">{c.product}</div>
                  <h2 className="headline-hashicorp text-white text-2xl sm:text-3xl">{c.title}</h2>
                  <p className="body-hashicorp text-[#b2b6bd]">{c.body}</p>

                  <ul className="pt-2 grid gap-2.5">
                    {c.bullets.map((b) => (
                      <li key={b} className="flex items-start gap-3 text-sm text-[#e4e4e7]">
                        <Check className="h-4 w-4 text-[#00c9a7] mt-0.5 shrink-0" />
                        <span>{b}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Subsystem Graphic Card */}
                <div className="lg:col-span-5 hashicorp-card p-8 flex flex-col justify-between min-h-[280px]">
                  <div className="flex items-center justify-between border-b border-[rgba(178,182,189,0.12)] pb-4">
                    <div className="flex items-center gap-2">
                      <Icon className="h-5 w-5 text-[#844fba]" />
                      <span className="headline-hashicorp text-white text-base">{c.product}</span>
                    </div>
                    <span className="product-pill text-[11px]">{c.status}</span>
                  </div>

                  <div className="my-6 flex flex-col items-center justify-center text-center gap-2">
                    <div className="flex h-14 w-14 items-center justify-center rounded-md bg-[#242424] border border-[rgba(178,182,189,0.12)]">
                      <Icon className="h-7 w-7 text-[#844fba]" />
                    </div>
                    <div className="text-base font-mono font-bold text-white">{c.metric}</div>
                    <div className="text-xs text-[#b2b6bd]">100% Local PC Hardware Persistence</div>
                  </div>

                  <div className="flex items-center justify-between text-xs text-[#b2b6bd] font-mono pt-3 border-t border-[rgba(178,182,189,0.12)]">
                    <span>STATUS: READY</span>
                    <span className="text-[#00c9a7] font-semibold flex items-center gap-1">
                      <ShieldCheck className="h-3.5 w-3.5" /> 100% LOCAL PRIVACY
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* CALL TO ACTION BANNER - DEDICATED DESKTOP EXE DOWNLOAD */}
      <section className="bg-[#000000] py-16 md:py-20 text-white">
        <div className="mx-auto max-w-4xl px-8 text-center">
          <div className="hashicorp-card p-10 md:p-12 text-center space-y-5 border-[rgba(178,182,189,0.2)] bg-[#141414]">
            <div className="eyebrow-hashicorp text-[#844fba]">STANDALONE DESKTOP APPLICATION</div>
            <h2 className="headline-hashicorp text-2xl sm:text-3xl text-white">
              Run Local RAG On Your Computer's Hardware.
            </h2>
            <p className="body-hashicorp text-sm text-[#b2b6bd] max-w-xl mx-auto">
              Download the standalone executable to process PubMed PDFs and lecture syllabi 100% offline on your machine.
            </p>
            <div className="pt-2">
              <a
                href="/downloads/InsightForge-Desktop.exe"
                download="InsightForge-Desktop.exe"
                className="btn-hashicorp-primary flex items-center justify-center gap-2 max-w-md mx-auto"
              >
                <Download className="w-4 h-4 text-black" />
                <span>Download Standalone Desktop App (.exe)</span>
              </a>
            </div>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}