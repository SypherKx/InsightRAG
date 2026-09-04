import React, { useState } from "react";
import { motion } from "framer-motion";
import { Download, Check, ShieldCheck, Play, FileArchive } from "lucide-react";

export const LocalInstallationGuide: React.FC = () => {
  const [downloading, setDownloading] = useState(false);
  const [showCli, setShowCli] = useState(false);

  const handleDirectDownload = (fileType: "exe" | "zip") => {
    setDownloading(true);
    const link = document.createElement("a");
    if (fileType === "zip") {
      link.href = "/downloads/InsightForge-Desktop.zip";
      link.download = "InsightForge-Desktop-Windows-x64.zip";
    } else {
      link.href = "/downloads/InsightForge-Desktop.exe";
      link.download = "InsightForge-Desktop.exe";
    }
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setTimeout(() => setDownloading(false), 2500);
  };

  return (
    <section className="bg-[#000000] text-white py-24 border-b border-[rgba(178,182,189,0.12)] relative" id="download-locally">
      <div className="mx-auto max-w-5xl px-6 sm:px-8 space-y-12">
        
        {/* Section Eyebrow Header */}
        <div className="text-center max-w-3xl mx-auto space-y-3">
          <div className="eyebrow-hashicorp">
            LOCAL ENGINE DEPLOYMENT // STANDALONE PACKAGE
          </div>
          <h2 className="display-hashicorp-lg text-white">
            Download InsightForge AI Desktop.
          </h2>
          <p className="body-hashicorp-lg max-w-xl mx-auto">
            Zero cloud server dependency. Includes local FAISS vector storage, PyTorch embeddings, and automated Ollama model detection.
          </p>
        </div>

        {/* HashiCorp Surface-1 Charcoal Card Container */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
          className="hashicorp-card max-w-3xl mx-auto text-center space-y-6"
        >
          <div className="space-y-2">
            <span className="product-pill font-mono text-[11px]">
              WINDOWS X64 STANDALONE • VERSION 1.0
            </span>
            <h3 className="headline-hashicorp text-white">
              InsightForge-Desktop.exe
            </h3>
            <p className="body-hashicorp max-w-lg mx-auto">
              Runs 100% offline on your PC. Includes embedded FastAPI server with zero cloud data transmission.
            </p>
          </div>

          {/* HashiCorp 8px Rounded CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
            <button
              onClick={() => handleDirectDownload("exe")}
              className="btn-hashicorp-primary w-full sm:w-auto"
            >
              <Download className="w-4 h-4 text-black" />
              <span>{downloading ? "Starting Download..." : "Download Desktop App (.exe)"}</span>
            </button>

            <button
              onClick={() => handleDirectDownload("zip")}
              className="btn-hashicorp-secondary w-full sm:w-auto"
            >
              <FileArchive className="w-4 h-4 text-white" />
              <span>Download Zip Archive</span>
            </button>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-6 text-xs text-[#b2b6bd] pt-4 border-t border-[rgba(178,182,189,0.12)]">
            <div className="flex items-center gap-1.5 font-medium">
              <Check className="w-4 h-4 text-[#00c9a7]" />
              <span>No GitHub Account Needed</span>
            </div>
            <div className="flex items-center gap-1.5 font-medium">
              <Check className="w-4 h-4 text-[#00c9a7]" />
              <span>1-Click Local Execution</span>
            </div>
            <div className="flex items-center gap-1.5 font-medium">
              <ShieldCheck className="w-4 h-4 text-[#00c9a7]" />
              <span>HIPAA & FERPA Ready</span>
            </div>
          </div>
        </motion.div>

        {/* 3 Step Cards */}
        <div className="grid gap-6 md:grid-cols-3">
          <div className="hashicorp-card space-y-3">
            <div className="eyebrow-hashicorp text-[#844fba]">STEP 01</div>
            <h4 className="card-title font-semibold text-white">Direct Download</h4>
            <p className="body-hashicorp-sm">
              Click the white download button to save <code className="text-[#844fba] font-mono text-xs">InsightForge-Desktop.exe</code>.
            </p>
          </div>

          <div className="hashicorp-card space-y-3">
            <div className="eyebrow-hashicorp text-[#f5a623]">STEP 02</div>
            <h4 className="card-title font-semibold text-white">Double-Click Run</h4>
            <p className="body-hashicorp-sm">
              Launch the standalone executable on Windows. Boots local Python backend & native desktop window.
            </p>
          </div>

          <div className="hashicorp-card space-y-3">
            <div className="eyebrow-hashicorp text-[#00bcff]">STEP 03</div>
            <h4 className="card-title font-semibold text-white">Upload & Query</h4>
            <p className="body-hashicorp-sm">
              Lands directly on <code className="text-[#00bcff] font-mono text-xs">/app/upload</code> to drag & drop medical PDFs or lab CSV datasets.
            </p>
          </div>
        </div>

        {/* Terminal Instructions */}
        <div className="text-center">
          <button
            onClick={() => setShowCli(!showCli)}
            className="eyebrow-hashicorp text-[#b2b6bd] hover:text-white transition-colors cursor-pointer"
          >
            {showCli ? "Hide developer terminal instructions" : "Looking for developer terminal commands?"}
          </button>

          {showCli && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 hashicorp-card max-w-2xl mx-auto text-left font-mono text-xs space-y-2 text-white border-[rgba(178,182,189,0.2)]"
            >
              <div className="text-[#656a76]"># Clone & run from terminal</div>
              <div>git clone https://github.com/SypherKx/InsightRAG.git</div>
              <div>cd InsightRAG && powershell -ExecutionPolicy Bypass -File .\launch.ps1</div>
            </motion.div>
          )}
        </div>

      </div>
    </section>
  );
};
