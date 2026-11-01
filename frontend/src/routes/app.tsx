import { createFileRoute, Outlet, redirect, Link } from "@tanstack/react-router";
import { Lock, LogIn, ArrowLeft, ShieldCheck, Sparkles } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

export const Route = createFileRoute("/app")({
  beforeLoad: ({ location }) => {
    if (location.pathname === "/app" || location.pathname === "/app/") {
      throw redirect({ to: "/app/upload" });
    }
  },
  component: ProtectedAppLayout,
});

function ProtectedAppLayout() {
  const { user, loading, openAuthModal } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex flex-col items-center justify-center text-white font-mono gap-3">
        <div className="w-8 h-8 border-2 border-[#ffe600] border-t-transparent rounded-full animate-spin" />
        <span className="text-xs text-gray-400">Verifying security credentials...</span>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-black text-white font-sans flex flex-col items-center justify-center p-4 selection:bg-[#ffe600] selection:text-black">
        <div className="max-w-md w-full bg-[#0d1117] border-2 border-black rounded-2xl shadow-[6px_6px_0px_#ffe600] p-6 sm:p-8 text-center space-y-6">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-black border-2 border-black shadow-[3px_3px_0px_#000] flex items-center justify-center">
            <Lock className="w-7 h-7 text-[#ffe600] animate-pulse" />
          </div>

          <div className="space-y-2">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#ffe600] text-black font-mono font-black text-[10px] border border-black">
              <ShieldCheck className="w-3.5 h-3.5 text-black" />
              <span>ENTERPRISE GUARD // ZERO-TRUST</span>
            </div>
            <h2 className="text-2xl font-black tracking-tight text-white font-sans">
              Access Restricted
            </h2>
            <p className="text-xs text-gray-400 font-mono leading-relaxed">
              InsightRAG AI Studio requires an authenticated session to upload confidential documents, query vector indexes, and run root-cause analysis.
            </p>
          </div>

          <div className="flex flex-col gap-3 pt-2">
            <button
              onClick={openAuthModal}
              className="w-full bg-[#ffe600] text-black hover:bg-yellow-400 font-mono font-black text-xs py-3 rounded-xl border-2 border-black shadow-[3px_3px_0px_#000] flex items-center justify-center gap-2 cursor-pointer transition active:translate-x-[1px] active:translate-y-[1px]"
            >
              <LogIn className="w-4 h-4 text-black" />
              <span>SIGN IN TO UNLOCK STUDIO</span>
            </button>

            <Link
              to="/"
              className="w-full bg-[#161b22] text-gray-300 hover:text-white font-mono font-bold text-xs py-2.5 rounded-xl border border-gray-700 flex items-center justify-center gap-1.5 transition"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Return to Overview</span>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return <Outlet />;
}
