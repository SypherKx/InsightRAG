import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface PremiumButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:
    | "primaryPill"
    | "outlineOnDark"
    | "outlineOnLight"
    | "aloePill"
    | "primary"
    | "secondary";
  size?: "sm" | "md" | "lg";
  children: ReactNode;
}

export function PremiumButton({
  variant = "primaryPill",
  size = "md",
  children,
  className,
  ...props
}: PremiumButtonProps) {
  const sizeClasses = {
    sm: "px-4 py-2 text-sm",
    md: "px-6 py-3 text-base",
    lg: "px-8 py-4 text-base font-semibold",
  };

  const variantClasses = {
    primaryPill: "button-primary-pill",
    outlineOnDark: "button-outline-on-dark",
    outlineOnLight: "button-outline-on-light",
    aloePill: "button-aloe-pill",
    primary: "button-primary-pill",
    secondary: "button-outline-on-dark",
  };

  return (
    <button
      className={cn(
        "cursor-pointer inline-flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200",
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
