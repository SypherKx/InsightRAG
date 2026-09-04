import React, { useEffect, useState } from 'react';
import { CheckCircle2, AlertTriangle, Download, Cpu, Server, Database, Sparkles, RefreshCw } from 'lucide-react';

interface SystemHealth {
  backend_status: string;
  version: string;
  database_status: string;
  vectorstore_status: string;
  ollama_running: boolean;
  target_model: string;
  model_installed: boolean;
  installed_models: string[];
  message: string;
}

export const SystemSetupModal: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [installing, setInstalling] = useState(false);
  const [pullProgress, setPullProgress] = useState<{ status: string; percent: number; completed: number; total: number }>({
    status: '',
    percent: 0,
    completed: 0,
    total: 0,
  });
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState(false);

  const fetchHealth = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/system/health');
      if (res.ok) {
        const data: SystemHealth = await res.json();
        setHealth(data);
        setErrorMsg(null);
      } else {
        setErrorMsg('Backend API error');
      }
    } catch (err) {
      setErrorMsg('Cannot reach backend on http://127.0.0.1:8000');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const handlePullModel = async () => {
    if (!health?.target_model) return;
    setInstalling(true);
    setPullProgress({ status: 'Starting model download...', percent: 0, completed: 0, total: 0 });

    try {
      const response = await fetch('http://127.0.0.1:8000/api/v1/system/pull-model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_name: health.target_model }),
      });

      if (!response.body) throw new Error('ReadableStream not supported');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            if (data.status) {
              setPullProgress({
                status: data.status,
                percent: data.percent || 0,
                completed: data.completed || 0,
                total: data.total || 0,
              });
            }
          } catch (e) {
            // parsing error ignored for chunk stream
          }
        }
      }

      await fetchHealth();
    } catch (err: any) {
      setErrorMsg(`Model download error: ${err.message}`);
    } finally {
      setInstalling(false);
    }
  };

  if (dismissed || (health?.ollama_running && health?.model_installed && !loading)) {
    return null; // All green or dismissed by user
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md p-4 transition-all">
      <div className="w-full max-w-xl bg-card/95 border border-border/60 rounded-2xl shadow-2xl p-6 md:p-8 space-y-6 text-card-foreground">
        
        {/* Header */}
        <div className="flex items-start justify-between border-b border-border/40 pb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary animate-pulse" />
              <h2 className="text-xl font-bold tracking-tight">InsightForge Desktop Health Check</h2>
            </div>
            <p className="text-xs text-muted-foreground">
              Automated local system & AI engine diagnostics
            </p>
          </div>
          <button
            onClick={fetchHealth}
            className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors"
            title="Refresh status"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Status Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          
          {/* 1. FastAPI Backend */}
          <div className="p-3.5 rounded-xl border bg-background/50 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Server className="w-5 h-5 text-emerald-500" />
              <div>
                <div className="text-xs font-semibold">FastAPI Backend</div>
                <div className="text-[10px] text-muted-foreground">localhost:8000</div>
              </div>
            </div>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>

          {/* 2. Vector DB */}
          <div className="p-3.5 rounded-xl border bg-background/50 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Database className="w-5 h-5 text-cyan-500" />
              <div>
                <div className="text-xs font-semibold">FAISS Vector Engine</div>
                <div className="text-[10px] text-muted-foreground">all-MiniLM-L6-v2</div>
              </div>
            </div>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>

          {/* 3. Ollama Service */}
          <div className={`p-3.5 rounded-xl border flex items-center justify-between ${
            health?.ollama_running ? 'bg-background/50 border-border' : 'bg-amber-500/10 border-amber-500/30'
          }`}>
            <div className="flex items-center gap-3">
              <Cpu className={`w-5 h-5 ${health?.ollama_running ? 'text-amber-500' : 'text-muted-foreground'}`} />
              <div>
                <div className="text-xs font-semibold">Ollama Engine</div>
                <div className="text-[10px] text-muted-foreground">localhost:11434</div>
              </div>
            </div>
            {health?.ollama_running ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-amber-500" />
            )}
          </div>

          {/* 4. Target Model */}
          <div className={`p-3.5 rounded-xl border flex items-center justify-between ${
            health?.model_installed ? 'bg-background/50 border-border' : 'bg-primary/10 border-primary/30'
          }`}>
            <div className="flex items-center gap-3">
              <Sparkles className={`w-5 h-5 ${health?.model_installed ? 'text-primary' : 'text-primary animate-pulse'}`} />
              <div>
                <div className="text-xs font-semibold">RAG Model</div>
                <div className="text-[10px] text-muted-foreground">{health?.target_model || 'llama3.2:3b'}</div>
              </div>
            </div>
            {health?.model_installed ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            ) : (
              <span className="text-[10px] bg-primary/20 text-primary px-2 py-0.5 rounded-full font-medium">Missing</span>
            )}
          </div>
        </div>

        {/* Dynamic Action Section */}
        {installing ? (
          <div className="p-4 rounded-xl bg-primary/10 border border-primary/20 space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-primary">{pullProgress.status}</span>
              <span className="font-mono text-xs">{pullProgress.percent}%</span>
            </div>
            <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-300 rounded-full"
                style={{ width: `${pullProgress.percent}%` }}
              />
            </div>
            <p className="text-[10px] text-muted-foreground text-center animate-pulse">
              Downloading AI weights directly from Ollama registry (~2.0 GB)... Please wait.
            </p>
          </div>
        ) : health?.ollama_running && !health?.model_installed ? (
          <div className="p-4 rounded-xl bg-card border border-primary/30 space-y-3 text-center">
            <h4 className="text-sm font-semibold text-foreground">AI Model Installation Needed</h4>
            <p className="text-xs text-muted-foreground">
              To run RAG & clinical explanations locally without server dependency, download the lightweight{' '}
              <strong className="text-foreground">{health.target_model}</strong> model (1-click automatic download).
            </p>
            <button
              onClick={handlePullModel}
              className="w-full py-2.5 px-4 bg-primary text-primary-foreground font-semibold rounded-xl hover:opacity-90 transition-opacity flex items-center justify-center gap-2 shadow-lg shadow-primary/25 text-xs"
            >
              <Download className="w-4 h-4" />
              Auto-Download {health.target_model} Model Now
            </button>
          </div>
        ) : !health?.ollama_running && !loading ? (
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 space-y-3 text-left">
            <h4 className="text-sm font-semibold text-amber-500 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" /> Ollama Service Not Detected
            </h4>
            <p className="text-xs text-muted-foreground">
              InsightForge runs AI models locally via Ollama. Please install Ollama or make sure it is running on your computer.
            </p>
            <div className="flex items-center gap-3 pt-1">
              <a
                href="https://ollama.com/download"
                target="_blank"
                rel="noreferrer"
                className="py-2 px-3 bg-foreground text-background text-xs font-semibold rounded-lg hover:opacity-90 flex items-center gap-1.5"
              >
                <Download className="w-3.5 h-3.5" /> Download Ollama
              </a>
              <button
                onClick={() => setDismissed(true)}
                className="text-xs text-muted-foreground hover:underline"
              >
                Continue using Groq Cloud API instead
              </button>
            </div>
          </div>
        ) : null}

        {/* Footer */}
        <div className="flex items-center justify-between text-[11px] text-muted-foreground border-t border-border/40 pt-3">
          <span>100% Local RAG Privacy Enabled</span>
          <button onClick={() => setDismissed(true)} className="hover:underline">
            Dismiss Warning
          </button>
        </div>

      </div>
    </div>
  );
};
