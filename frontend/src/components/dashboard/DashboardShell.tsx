import type { ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { AmbientBackground } from "@/components/premium/AmbientBackground";
import { ArrowLeft, Sparkles, BookOpen } from "lucide-react";

export function DashboardShell({ children }: { children: ReactNode }) {
  return (
    <div className="relative flex min-h-screen text-white bg-[#000000] transition-colors duration-300 overflow-x-hidden">
      <AmbientBackground />
      <main className="min-w-0 flex-1 scrollbar-thin">{children}</main>
    </div>
  );
}

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3.5 sm:gap-4 border-b border-white/10 bg-[#0a0a0a] px-4 sm:px-6 md:px-8 py-4 sm:py-6 md:flex-row md:items-end md:justify-between transition-colors duration-300">
      <div className="space-y-1.5 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <Link
            to="/app/upload"
            className="inline-flex items-center gap-1.5 text-xs font-mono font-bold text-[#ffe600] hover:underline"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Studio Workspace</span>
          </Link>
          <span className="text-gray-600">•</span>
          <Link to="/" className="text-xs font-mono text-gray-400 hover:text-white">
            Home
          </Link>
          <span className="text-gray-600">•</span>
          <Link to="/docs" className="text-xs font-mono text-gray-400 hover:text-white">
            Docs
          </Link>
        </div>
        <h1 className="heading-xl text-xl sm:text-2xl md:text-3xl font-bold tracking-tight text-white">
          {title}
        </h1>
        {description && <p className="body-md text-xs sm:text-sm text-[#9dabad] leading-relaxed">{description}</p>}
      </div>
      {action && <div className="flex flex-wrap items-center gap-2 pt-1 md:pt-0 shrink-0">{action}</div>}
    </div>
  );
}

