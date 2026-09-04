import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  variant?:
    | "canvas"
    | "soft"
    | "dark"
    | "coral"
    | "forest"
    | "cream"
    | "peach"
    | "mint"
    | "yellow"
    | "violet"
    | "cyan";
  hover?: boolean;
}

export function GlassCard({
  children,
  className,
  variant = "canvas",
  hover = false,
}: GlassCardProps) {
  const variantStyles = {
    canvas: "bg-[#0a0a0a] border border-white/10 text-white rounded-xl p-6 shadow-sm",
    soft: "bg-[#141414] border border-white/10 text-white rounded-xl p-6",
    dark: "bg-[#0a0a0a] text-white border border-white/10 rounded-xl p-8 shadow-xl",
    coral: "bg-[#0a0a0a] text-white border border-white/10 rounded-xl p-8 shadow-lg",
    forest: "bg-[#c1fbd4] text-[#000000] border border-[#a3f7be] rounded-xl p-8 shadow-lg",
    cream: "bg-[#fbfbf5] text-[#000000] border border-[#e4e4e7] rounded-xl p-6 shadow-sm",
    peach: "bg-[#141414] text-white border border-white/10 rounded-xl p-6",
    mint: "bg-[#c1fbd4] text-[#000000] border border-[#a3f7be] rounded-xl p-6",
    yellow: "bg-[#d4f9e0] text-[#000000] border border-[#a3f7be] rounded-xl p-6",
    violet: "bg-[#141414] text-white border border-white/10 rounded-xl p-8 shadow-lg",
    cyan: "bg-[#141414] text-white border border-white/10 rounded-xl p-8 shadow-lg",
  };

  return (
    <div
      className={cn(
        variantStyles[variant],
        "transition-all duration-200",
        hover && "hover:border-white/30 hover:shadow-md",
        className,
      )}
    >
      {children}
    </div>
  );
}
