import { Link, useRouterState } from "@tanstack/react-router";
import { Download } from "lucide-react";
import { BrandLogo } from "@/components/brand/BrandLogo";
import { cn } from "@/lib/utils";

const links = [
  { to: "/", label: "Overview" },
  { to: "/features", label: "Capabilities" },
  { to: "/about", label: "Architecture" },
] as const;

export function Navbar() {
  const path = useRouterState({ select: (s) => s.location.pathname });

  return (
    <header className="sticky top-0 z-50 h-16 w-full border-b border-[rgba(178,182,189,0.12)] bg-[#000000]/95 backdrop-blur-md transition-colors duration-200">
      <div className="mx-auto flex h-full max-w-7xl items-center justify-between px-6 sm:px-8">
        {/* HashiCorp Text Brand Masthead */}
        <Link to="/" className="flex items-center gap-2">
          <BrandLogo size="md" />
        </Link>

        {/* Primary Navigation */}
        <nav className="hidden items-center gap-8 md:flex">
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

        {/* White Rounded 8px CTA - Direct Executable Download */}
        <div className="flex items-center gap-4">
          <a
            href="/downloads/InsightForge-Desktop.exe"
            download="InsightForge-Desktop.exe"
            className="btn-hashicorp-primary"
          >
            <Download className="w-4 h-4 text-black" />
            <span>Download Desktop App (.exe)</span>
          </a>
        </div>
      </div>
    </header>
  );
}
