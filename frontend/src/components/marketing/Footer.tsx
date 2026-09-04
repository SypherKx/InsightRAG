import { Link } from "@tanstack/react-router";
import { BrandLogo } from "@/components/brand/BrandLogo";

export function Footer() {
  return (
    <footer className="bg-[var(--surface-dark)] text-[var(--on-dark)] border-t border-white/10 py-16 transition-colors duration-300">
      <div className="mx-auto max-w-7xl px-6">
        {/* Custom Vector Brand Logo */}
        <div className="mb-12">
          <Link to="/">
            <BrandLogo size="lg" />
          </Link>
        </div>

        {/* 4-Column Directory Grid */}
        <div className="grid gap-12 md:grid-cols-4">
          <div className="flex flex-col gap-3 text-sm">
            <div className="caption-uppercase text-[var(--on-dark-soft)] mb-1">Desktop Product</div>
            <a href="/#download-locally" className="text-[var(--on-dark-soft)] hover:text-[var(--on-dark)] transition">
              1-Click Desktop Installer
            </a>
            <a href="/#download-locally" className="text-[var(--on-dark-soft)] hover:text-[var(--on-dark)] transition">
              Local FAISS RAG Search
            </a>
            <a href="/#download-locally" className="text-[var(--on-dark-soft)] hover:text-[var(--on-dark)] transition">
              Ollama Llama 3.2 Setup
            </a>
            <a href="/#download-locally" className="text-[var(--on-dark-soft)] hover:text-[var(--on-dark)] transition">
              Terminal / CLI Installation
            </a>
          </div>

          <div className="flex flex-col gap-3 text-sm">
            <div className="caption-uppercase text-[var(--on-dark-soft)] mb-1">Solutions</div>
            <Link to="/features" className="text-[var(--on-dark-soft)] hover:text-[var(--on-dark)] transition">
              Hospital Wards & ICUs
            </Link>
            <Link to="/features" className="text-[var(--on-dark-soft)] hover:text-[var(--on-dark)] transition">
              Medical Research Labs
            </Link>
            <Link to="/about" className="text-[var(--on-dark-soft)] hover:text-[var(--on-dark)] transition">
              University Faculties
            </Link>
            <a href="#pricing" className="text-[var(--on-dark-soft)] hover:text-[var(--on-dark)] transition">
              Commercial Plans
            </a>
          </div>

          <div className="flex flex-col gap-3 text-sm">
            <div className="caption-uppercase text-[var(--on-dark-soft)] mb-1">Research & Privacy</div>
            <a href="#" className="text-[var(--on-dark-soft)] hover:text-[var(--on-dark)] transition">
              FAISS Vector Benchmarks
            </a>
            <a href="#" className="text-[var(--on-dark-soft)] hover:text-[var(--on-dark)] transition">
              HIPAA & FERPA Compliance
            </a>
            <a href="#" className="text-[var(--on-dark-soft)] hover:text-[var(--on-dark)] transition">
              Model Safety Cards
            </a>
            <a href="#" className="text-[var(--on-dark-soft)] hover:text-[var(--on-dark)] transition">
              Documentation
            </a>
          </div>

          <div className="flex flex-col gap-3 text-sm">
            <div className="caption-uppercase text-[var(--on-dark-soft)] mb-1">Company</div>
            <Link to="/about" className="text-[var(--on-dark-soft)] hover:text-[var(--on-dark)] transition">
              About InsightRAG
            </Link>
            <a href="#" className="text-[var(--on-dark-soft)] hover:text-[var(--on-dark)] transition">
              Careers
            </a>
            <a href="#" className="text-[var(--on-dark-soft)] hover:text-[var(--on-dark)] transition">
              Privacy Policy
            </a>
            <a href="#" className="text-[var(--on-dark-soft)] hover:text-[var(--on-dark)] transition">
              Terms of Service
            </a>
          </div>
        </div>

        {/* Copyright Footer Line */}
        <div className="mt-16 border-t border-white/10 pt-8 flex flex-col md:flex-row md:items-center justify-between text-xs text-[var(--on-dark-soft)]">
          <div>© {new Date().getFullYear()} InsightRAG AI. Made by <span className="text-white">Karan Pratap Singh</span>.</div>
          <div className="mt-2 md:mt-0">Autonomous Multimodal Retrieval-Augmented Generation</div>
        </div>
      </div>
    </footer>
  );
}