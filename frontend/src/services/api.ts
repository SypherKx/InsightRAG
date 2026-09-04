import axios from "axios";
import type {
  DatasetListResponse,
  AnomalyListResponse,
  AnomalyDetail,
  UploadResponse,
  Dataset,
} from "../types/backend-types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

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

export async function uploadRAGDocuments(files: File[]): Promise<any> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
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
): Promise<any> {
  const { data } = await api.post(
    "/rag/query",
    {
      query,
      top_k: topK,
      min_score: minScore,
      model,
      generate_answer: true,
    },
    {
      timeout: 120000, // 2 minutes for vector search + Ollama LLM inference
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

export default api;
