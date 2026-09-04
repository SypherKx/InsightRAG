import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface GlowBadgeProps {
  children: ReactNode;
  variant?: "mint" | "shade" | "default" | "darkOutline";
  className?: string;
}

export function GlowBadge({ children, variant = "mint", className }: GlowBadgeProps) {
  const variantStyles = {
    mint: "pill-tag-mint",
    shade: "pill-tag-shade",
    default: "pill-tag-mint",
    darkOutline:
      "border border-white/20 bg-black/40 text-white rounded-full px-3 py-1 text-xs font-mono tracking-wider uppercase",
  };

  return (
    <span className={cn("inline-flex items-center gap-1.5", variantStyles[variant], className)}>
      {children}
    </span>
  );
}
