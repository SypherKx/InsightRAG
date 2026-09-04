import type { ReactNode } from "react";
import { AmbientBackground } from "@/components/premium/AmbientBackground";

export function DashboardShell({ children }: { children: ReactNode }) {
  return (
    <div className="relative flex min-h-screen text-white bg-[#000000] transition-colors duration-300">
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
    <div className="flex flex-col gap-4 border-b border-white/10 bg-[#0a0a0a] px-8 py-6 md:flex-row md:items-end md:justify-between transition-colors duration-300">
      <div>
        <h1 className="heading-xl text-2xl font-bold tracking-tight text-white md:text-3xl">
          {title}
        </h1>
        {description && <p className="body-md mt-1 text-sm text-[#9dabad]">{description}</p>}
      </div>
      {action}
    </div>
  );
}
