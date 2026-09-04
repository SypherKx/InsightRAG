import type { ReactNode } from "react";
import { AmbientBackground } from "@/components/premium/AmbientBackground";
import { Navbar } from "./Navbar";
import { Footer } from "./Footer";

export function MarketingLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-screen bg-canvas text-ink">
      <AmbientBackground />
      <Navbar />
      <main>{children}</main>
      <Footer />
    </div>
  );
}
