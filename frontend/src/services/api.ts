import axios from "axios";
import type {
  DatasetListResponse,
  AnomalyListResponse,
  AnomalyDetail,
  UploadResponse,
  Dataset,
} from "../types/backend-types";

const getApiBase = () => {
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL;
  if (typeof window !== "undefined" && window.location?.hostname) {
    const host = window.location.hostname;
    const protocol = window.location.protocol === "https:" ? "https:" : "http:";
    return `${protocol}//${host}:8000/api/v1`;
  }
  return "http://localhost:8000/api/v1";
};

const API_BASE = getApiBase();

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000, // 2 minute timeout — embedding generation & Ollama inference need time
});

// ─── Datasets ───

export async function uploadDataset(
  file: File,
  name?: string,
  timeColumn?: string,
  dimensions?: string,
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (name) formData.append("name", name);
  if (timeColumn) formData.append("time_column", timeColumn);
  if (dimensions) formData.append("dimensions", dimensions);

  const { data } = await api.post("/datasets/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getDatasets(
  page = 1,
  perPage = 20,
  status?: string,
): Promise<DatasetListResponse> {
  try {
    const params: Record<string, any> = { page, per_page: perPage };
    if (status) params.status = status;
    const { data } = await api.get("/datasets", { params });
    return data;
  } catch (err) {
    return { datasets: [], total: 0, page: 1, per_page: perPage } as any;
  }
}

export async function getDataset(id: string): Promise<Dataset> {
  const { data } = await api.get(`/datasets/${id}`);
  return data;
}

export async function deleteDataset(id: string): Promise<void> {
  await api.delete(`/datasets/${id}`);
}

// ─── Anomalies ───

export async function getAnomalies(
  datasetId: string,
  params?: {
    severity_min?: number;
    anomaly_type?: string;
    metric?: string;
    page?: number;
    per_page?: number;
  },
): Promise<AnomalyListResponse> {
  try {
    const { data } = await api.get(`/datasets/${datasetId}/anomalies`, { params });
    return data;
  } catch (err) {
    return { anomalies: [], total: 0, page: 1, per_page: 20 } as any;
  }
}

export async function getAnomalyDetail(anomalyId: string): Promise<AnomalyDetail> {
  const { data } = await api.get(`/anomalies/${anomalyId}`);
  return data;
}

// ─── Health ───

export async function checkHealth(): Promise<any> {
  try {
    const { data } = await api.get("/health");
    return data;
  } catch (err) {
    return { status: "offline", rag_enabled: false };
  }
}

// ─── RAG Query & Upload ───

export async function uploadRAGDocuments(
  files: File[],
  startPage?: number,
  endPage?: number
): Promise<any> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  if (startPage !== undefined && startPage !== null && !isNaN(startPage)) {
    formData.append("start_page", startPage.toString());
  }
  if (endPage !== undefined && endPage !== null && !isNaN(endPage)) {
    formData.append("end_page", endPage.toString());
  }
  const { data } = await api.post("/rag/documents", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 180000, // 3 minutes for document chunking + embedding generation
  });
  return data;
}

export async function queryRAG(
  query: string,
  topK = 5,
  minScore = 0.0,
  model = "llama3.2:3b",
  processingMode = "local",
  apiKey?: string,
  history?: Array<{ role: string; text?: string; content?: string }>
): Promise<any> {
  const { data } = await api.post(
    "/rag/query",
    {
      query,
      top_k: topK,
      min_score: minScore,
      model,
      generate_answer: true,
      processing_mode: processingMode,
      api_key: apiKey,
      history: history || [],
    },
    {
      timeout: 120000, // 2 minutes for vector search + inference
    },
  );
  return data;
}

export async function getRAGStats(): Promise<any> {
  try {
    const { data } = await api.get("/rag/stats");
    return data;
  } catch (err) {
    return { total_vectors: 0, files: [] };
  }
}

export async function clearRAGKnowledgeBase(): Promise<any> {
  const { data } = await api.post("/rag/clear");
  return data;
}

export async function deleteRAGDocument(docName: string): Promise<any> {
  const { data } = await api.delete(`/rag/documents/${encodeURIComponent(docName)}`);
  return data;
}

export async function getSystemSpecs(): Promise<any> {
  try {
    const { data } = await api.get("/system/specs");
    return data;
  } catch (err) {
    return {
      cpu_threads: 12,
      ram_gb: 15.4,
      gpu_name: "Integrated / CPU",
      vram_gb: 0.0,
      has_gpu: false,
      acceleration_mode: "CPU PARALLEL ENGINE",
      ollama_running: true,
      installed_models: ["llama3.2:3b"],
    };
  }
}

export async function pullModel(modelName: string): Promise<any> {
  const { data } = await api.post("/system/pull-model", { model_name: modelName });
  return data;
}

export async function setHardwareMode(mode: "gpu" | "cpu"): Promise<any> {
  const { data } = await api.post("/system/hardware-mode", { mode });
  return data;
}

export async function getHardwareMode(): Promise<any> {
  const { data } = await api.get("/system/hardware-mode");
  return data;
}

// ─── SSE Streaming RAG Query ───

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onMetadata: (data: any) => void;
  onDone: (data: any) => void;
  onError: (error: string) => void;
}

export async function streamRAGQuery(
  query: string,
  topK = 5,
  minScore = 0.0,
  model = "llama3.2:3b",
  processingMode = "local",
  apiKey?: string,
  history?: Array<{ role: string; text?: string; content?: string }>,
  callbacks?: StreamCallbacks,
): Promise<void> {
  const url = `${API_BASE}/rag/query/stream`;
  const body = {
    query,
    top_k: topK,
    min_score: minScore,
    model,
    generate_answer: true,
    processing_mode: processingMode,
    api_key: apiKey,
    history: history || [],
  };

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    callbacks?.onError(`Server error: ${response.status}`);
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    callbacks?.onError("No stream reader available");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      let currentEvent = "message";
      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          const raw = line.slice(6).trim();
          if (!raw) continue;
          try {
            const parsed = JSON.parse(raw);
            if (currentEvent === "token") {
              callbacks?.onToken(parsed.token || "");
            } else if (currentEvent === "metadata") {
              callbacks?.onMetadata(parsed);
            } else if (currentEvent === "done") {
              callbacks?.onDone(parsed);
            } else if (currentEvent === "error") {
              callbacks?.onError(parsed.error || "Stream error");
            }
          } catch {
            // skip malformed JSON
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export default api;
