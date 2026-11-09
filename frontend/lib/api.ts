const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api";

export interface DatasetItem {
  id: string;
  name: string;
  dataset_type: string;
  hdfs_path: string;
  size_bytes: number;
  row_count: number;
  column_count: number;
  columns: string[];
  uploaded_at: string;
}

export interface DatasetSummary {
  total_files: number;
  total_size_bytes: number;
  total_rows: number;
  meets_1m_target: boolean;
  breakdown_by_type: Record<string, { count: number; rows: number; size_bytes: number }>;
}

export interface DatasetPreview {
  id: string;
  name: string;
  total_rows: number;
  columns: string[];
  preview_rows: Record<string, string | number>[];
}

export async function fetchDatasets(): Promise<DatasetItem[]> {
  const res = await fetch(`${API_BASE}/datasets`);
  if (!res.ok) throw new Error("Gagal mengambil daftar dataset.");
  return res.json();
}

export async function fetchDatasetSummary(): Promise<DatasetSummary> {
  const res = await fetch(`${API_BASE}/datasets/summary`);
  if (!res.ok) throw new Error("Gagal mengambil ringkasan dataset.");
  return res.json();
}

export async function fetchDatasetPreview(id: string, limit = 20): Promise<DatasetPreview> {
  const res = await fetch(`${API_BASE}/datasets/${id}/preview?limit=${limit}`);
  if (!res.ok) throw new Error("Gagal mengambil preview dataset.");
  return res.json();
}

export async function deleteDataset(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/datasets/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Gagal menghapus dataset.");
}

export async function uploadDatasetInChunks(
  file: File,
  datasetType: string,
  onProgress?: (pct: number) => void
): Promise<DatasetItem> {
  const chunkSize = 8 * 1024 * 1024; // 8MB per chunk
  const totalChunks = Math.ceil(file.size / chunkSize);

  // 1. Init upload
  const initRes = await fetch(`${API_BASE}/datasets/upload/init`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename: file.name,
      dataset_type: datasetType,
      total_size: file.size,
      total_chunks: totalChunks
    })
  });
  if (!initRes.ok) {
    const err = await initRes.json();
    throw new Error(err.detail || "Gagal inisialisasi upload.");
  }
  const { upload_id } = await initRes.json();

  // 2. Upload chunks sequentially
  for (let index = 0; index < totalChunks; index++) {
    const start = index * chunkSize;
    const end = Math.min(start + chunkSize, file.size);
    const chunkBlob = file.slice(start, end);

    const formData = new FormData();
    formData.append("upload_id", upload_id);
    formData.append("chunk_index", index.toString());
    formData.append("file", chunkBlob, `${file.name}.part${index}`);

    const chunkRes = await fetch(`${API_BASE}/datasets/upload/chunk`, {
      method: "POST",
      body: formData
    });
    if (!chunkRes.ok) {
      throw new Error(`Gagal mengunggah chunk ke-${index}`);
    }

    if (onProgress) {
      onProgress(Math.round(((index + 1) / totalChunks) * 100));
    }
  }

  // 3. Complete upload
  const completeRes = await fetch(`${API_BASE}/datasets/upload/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ upload_id })
  });
  if (!completeRes.ok) {
    const err = await completeRes.json();
    throw new Error(err.detail || "Gagal memproses penggabungan dan upload ke HDFS.");
  }

  return completeRes.json();
}
