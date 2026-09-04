import { Link } from "@tanstack/react-router";

export function BrandLogo({ size = "md", disableLink = false }: { size?: "sm" | "md" | "lg"; disableLink?: boolean }) {
  const textSizes = {
    sm: "text-lg",
    md: "text-xl",
    lg: "text-2xl",
  };

  const content = (
    <div className="flex items-center gap-2 select-none font-sans font-bold tracking-tight text-white">
      <span className={`${textSizes[size]}`}>
        InsightRAG <span className="text-[#844fba]">AI</span>
      </span>
    </div>
  );

  if (disableLink) {
    return content;
  }

  return (
    <Link to="/" className="inline-flex items-center no-underline hover:opacity-90 transition-opacity">
      {content}
    </Link>
  );
}
