import { Link, useRouterState } from "@tanstack/react-router";
import { useState } from "react";
import { Download, Menu, X, Sparkles, BookOpen, Layers, Terminal } from "lucide-react";
import { BrandLogo } from "@/components/brand/BrandLogo";
import { cn } from "@/lib/utils";

const links = [
  { to: "/", label: "Overview" },
  { to: "/features", label: "Capabilities" },
  { to: "/about", label: "Architecture" },
  { to: "/docs", label: "Documentation" },
] as const;

export function Navbar() {
  const path = useRouterState({ select: (s) => s.location.pathname });
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-[rgba(178,182,189,0.12)] bg-[#000000]/95 backdrop-blur-md transition-colors duration-200">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand Logo */}
        <Link to="/" className="flex items-center gap-2" onClick={() => setMobileMenuOpen(false)}>
          <BrandLogo size="md" />
        </Link>

        {/* Primary Desktop Navigation */}
        <nav className="hidden items-center gap-6 lg:gap-8 md:flex">
          {links.map((l) => {
            const active = path === l.to;
            return (
              <Link
                key={l.to}
                to={l.to}
                className={cn(
                  "text-sm font-medium transition-colors tracking-tight",
                  active
                    ? "text-white font-semibold underline underline-offset-8 decoration-2 decoration-[#844fba]"
                    : "text-[#b2b6bd] hover:text-white",
                )}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>

        {/* Action Buttons & Mobile Hamburger Toggle */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Studio Link for fast access */}
          <Link
            to="/app/upload"
            className="hidden sm:inline-flex items-center gap-1.5 bg-[#ffe600] text-black font-mono font-black text-xs px-3 py-2 rounded-lg border border-black hover:bg-yellow-400 transition active:scale-95"
          >
            <Sparkles className="w-3.5 h-3.5 text-black" />
            <span>Open Studio</span>
          </Link>

          {/* Desktop App Download CTA */}
          <a
            href="/downloads/InsightForge-Desktop.exe"
            download="InsightForge-Desktop.exe"
            className="btn-hashicorp-primary text-xs sm:text-sm !h-9 sm:!h-10 px-3 sm:px-4"
            title="Download Standalone Windows Desktop App"
          >
            <Download className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-black shrink-0" />
            <span className="hidden sm:inline">Download (.exe)</span>
            <span className="sm:hidden">App (.exe)</span>
          </a>

          {/* Mobile Hamburger Button */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden flex items-center justify-center p-2 rounded-lg bg-[#141414] border border-[rgba(178,182,189,0.2)] text-white hover:bg-[#242424] transition active:scale-95"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Animated Dropdown Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-[rgba(178,182,189,0.15)] bg-[#0a0a0a] px-4 py-4 space-y-3 font-sans animate-in slide-in-from-top-2 duration-200">
          <div className="flex flex-col space-y-1">
            {links.map((l) => {
              const active = path === l.to;
              return (
                <Link
                  key={l.to}
                  to={l.to}
                  onClick={() => setMobileMenuOpen(false)}
                  className={cn(
                    "flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                    active
                      ? "bg-[#1f1f1f] text-white font-bold border-l-2 border-[#844fba]"
                      : "text-[#b2b6bd] hover:bg-[#141414] hover:text-white",
                  )}
                >
                  <span>{l.label}</span>
                </Link>
              );
            })}
          </div>

          <div className="pt-2 border-t border-white/10 flex flex-col gap-2">
            <Link
              to="/app/upload"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full flex items-center justify-center gap-2 bg-[#ffe600] text-black font-mono font-black text-xs py-2.5 rounded-lg border border-black shadow-[2px_2px_0px_#000] active:scale-98"
            >
              <Sparkles className="w-4 h-4 text-black" />
              <span>Launch Local Studio Workspace</span>
            </Link>

            <Link
              to="/docs"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full flex items-center justify-center gap-2 bg-[#141414] hover:bg-[#242424] text-white font-mono font-bold text-xs py-2.5 rounded-lg border border-[rgba(178,182,189,0.2)]"
            >
              <BookOpen className="w-4 h-4 text-purple-400" />
              <span>View Documentation</span>
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
