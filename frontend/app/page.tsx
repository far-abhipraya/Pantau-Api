"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  UploadCloud,
  FileText,
  Trash2,
  Eye,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  Database,
  BarChart2,
  HardDrive
} from "lucide-react";
import {
  fetchDatasets,
  fetchDatasetSummary,
  fetchDatasetPreview,
  deleteDataset,
  uploadDatasetInChunks,
  DatasetItem,
  DatasetSummary,
  DatasetPreview
} from "@/lib/api";

export default function UploadPage() {
  const [datasets, setDatasets] = useState<DatasetItem[]>([]);
  const [summary, setSummary] = useState<DatasetSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedType, setSelectedType] = useState("firms_hist");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewData, setPreviewData] = useState<DatasetPreview | null>(null);
  const [statusMsg, setStatusMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [dsList, dsSum] = await Promise.all([fetchDatasets(), fetchDatasetSummary()]);
      setDatasets(dsList);
      setSummary(dsSum);
    } catch (err: any) {
      console.error(err);
      setStatusMsg({ type: "error", text: err.message || "Gagal memuat data dari server." });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (file.name.toLowerCase().endsWith(".csv")) {
        setSelectedFile(file);
      } else {
        setStatusMsg({ type: "error", text: "Hanya file berekstensi .csv yang diizinkan." });
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      if (file.name.toLowerCase().endsWith(".csv")) {
        setSelectedFile(file);
      } else {
        setStatusMsg({ type: "error", text: "Hanya file berekstensi .csv yang diizinkan." });
      }
    }
  };

  const startUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setUploadProgress(0);
    setStatusMsg(null);

    try {
      await uploadDatasetInChunks(selectedFile, selectedType, (pct) => {
        setUploadProgress(pct);
      });
      setStatusMsg({ type: "success", text: `Berhasil mengunggah ${selectedFile.name} ke HDFS!` });
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await loadData();
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Gagal mengunggah file." });
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Hapus dataset ${name} dari HDFS dan database?`)) return;
    try {
      await deleteDataset(id);
      setStatusMsg({ type: "success", text: `Dataset ${name} berhasil dihapus.` });
      await loadData();
      if (previewData?.id === id) setPreviewData(null);
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Gagal menghapus dataset." });
    }
  };

  const handlePreview = async (id: string) => {
    try {
      const data = await fetchDatasetPreview(id, 20);
      setPreviewData(data);
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Gagal memuat pratinjau dataset." });
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 font-sans">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center pb-6 border-b border-slate-800">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-emerald-400 flex items-center gap-3">
              <Database className="w-8 h-8 text-emerald-500" />
              KarhutlaWatch Data Ingestion
            </h1>
            <p className="text-slate-400 mt-1">
              Platform Big Data Pemantauan dan Prediksi Karhutla Indonesia (Hadoop HDFS, Spark, NiFi)
            </p>
          </div>
          <div className="mt-4 md:mt-0 flex gap-3">
            <button
              onClick={loadData}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-sm font-medium transition"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>
        </header>

        {/* Status Alerts */}
        {statusMsg && (
          <div
            className={`p-4 rounded-lg flex items-center gap-3 ${
              statusMsg.type === "success"
                ? "bg-emerald-950/80 border border-emerald-800 text-emerald-300"
                : "bg-rose-950/80 border border-rose-800 text-rose-300"
            }`}
          >
            {statusMsg.type === "success" ? (
              <CheckCircle className="w-5 h-5 flex-shrink-0" />
            ) : (
              <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            )}
            <span className="text-sm">{statusMsg.text}</span>
          </div>
        )}

        {/* Big Data KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl flex items-center gap-4">
            <div className="p-3 bg-emerald-950/80 border border-emerald-800/60 rounded-lg text-emerald-400">
              <BarChart2 className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium">TOTAL BARIS DATA MENTAH</p>
              <p className="text-2xl font-bold text-slate-100">
                {summary?.total_rows.toLocaleString() || "0"}
              </p>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl flex items-center gap-4">
            <div className="p-3 bg-blue-950/80 border border-blue-800/60 rounded-lg text-blue-400">
              <HardDrive className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium">TOTAL UKURAN HDFS</p>
              <p className="text-2xl font-bold text-slate-100">
                {((summary?.total_size_bytes || 0) / (1024 * 1024)).toFixed(2)} MB
              </p>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl flex items-center gap-4">
            <div className="p-3 bg-purple-950/80 border border-purple-800/60 rounded-lg text-purple-400">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium">FILE TERDAFTAR DI HDFS</p>
              <p className="text-2xl font-bold text-slate-100">{summary?.total_files || 0} File</p>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl flex items-center gap-4">
            <div
              className={`p-3 rounded-lg border ${
                summary?.meets_1m_target
                  ? "bg-emerald-950/80 border-emerald-800 text-emerald-400"
                  : "bg-amber-950/80 border-amber-800 text-amber-400"
              }`}
            >
              <CheckCircle className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium">TARGET DATA TUGAS AKHIR</p>
              <p
                className={`text-sm font-bold ${
                  summary?.meets_1m_target ? "text-emerald-400" : "text-amber-400"
                }`}
              >
                {summary?.meets_1m_target
                  ? "Tercapai (>= 1.000.000)"
                  : "Belum (Target >= 1.000.000)"}
              </p>
            </div>
          </div>
        </div>

        {/* Upload Section */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
            <UploadCloud className="w-5 h-5 text-emerald-400" />
            Unggah File Dataset CSV ke HDFS
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2">
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleFileDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition flex flex-col items-center justify-center min-h-[200px] ${
                  selectedFile
                    ? "border-emerald-500/80 bg-emerald-950/20"
                    : "border-slate-700 hover:border-slate-500 bg-slate-950/40"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <UploadCloud className="w-12 h-12 text-slate-400 mb-2" />
                {selectedFile ? (
                  <div>
                    <p className="font-semibold text-emerald-300">{selectedFile.name}</p>
                    <p className="text-xs text-slate-400 mt-1">
                      Ukuran: {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="font-medium text-slate-300">
                      Drag and drop file CSV ke sini, atau klik untuk memilih file
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Mendukung chunked upload hingga ukuran gigabyte langsung ke HDFS
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-4 flex flex-col justify-between">
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-400 mb-2">
                  Tipe Dataset
                </label>
                <select
                  value={selectedType}
                  onChange={(e) => setSelectedType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
                >
                  <option value="firms_hist">NASA FIRMS Historical (VIIRS / MODIS)</option>
                  <option value="firms_nrt">NASA FIRMS NRT (Near Real-Time)</option>
                  <option value="weather">Cuaca (ERA5 / CHIRPS)</option>
                  <option value="generic">Dataset Umum / Validasi</option>
                </select>
                <p className="text-xs text-slate-500 mt-2">
                  File akan otomatis distaging lalu diupload via{" "}
                  <code className="text-slate-400">hdfs dfs -put</code> ke direktori{" "}
                  <code className="text-emerald-400">/karhutla/raw/{selectedType}/</code>.
                </p>
              </div>

              {uploading && (
                <div className="space-y-2">
                  <div className="flex justify-between text-xs text-slate-300 font-medium">
                    <span>Mengunggah Chunk ke HDFS...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
                    <div
                      className="bg-emerald-500 h-full transition-all duration-200"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

              <button
                onClick={startUpload}
                disabled={!selectedFile || uploading}
                className="w-full py-2.5 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium text-sm transition flex items-center justify-center gap-2"
              >
                <UploadCloud className="w-4 h-4" />
                {uploading ? "Memproses Upload..." : "Mulai Upload ke HDFS"}
              </button>
            </div>
          </div>
        </div>

        {/* Dataset Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="p-5 border-b border-slate-800 flex justify-between items-center">
            <h2 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
              <FileText className="w-5 h-5 text-emerald-400" />
              Daftar Dataset di HDFS (<code className="text-sm font-normal text-slate-400">/karhutla/raw/</code>)
            </h2>
            <span className="text-xs text-slate-400">Total: {datasets.length} Dataset</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/60 text-slate-400 uppercase text-xs border-b border-slate-800">
                <tr>
                  <th className="py-3.5 px-4">Nama File</th>
                  <th className="py-3.5 px-4">Tipe</th>
                  <th className="py-3.5 px-4">Path HDFS</th>
                  <th className="py-3.5 px-4 text-right">Ukuran (MB)</th>
                  <th className="py-3.5 px-4 text-right">Jumlah Baris</th>
                  <th className="py-3.5 px-4 text-center">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {datasets.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500">
                      Belum ada dataset yang diunggah ke HDFS.
                    </td>
                  </tr>
                ) : (
                  datasets.map((ds) => (
                    <tr key={ds.id} className="hover:bg-slate-800/30 transition">
                      <td className="py-3 px-4 font-medium text-slate-200">{ds.name}</td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-xs bg-slate-800 border border-slate-700 text-slate-300">
                          {ds.dataset_type}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-xs text-slate-400">{ds.hdfs_path}</td>
                      <td className="py-3 px-4 text-right">
                        {(ds.size_bytes / (1024 * 1024)).toFixed(2)}
                      </td>
                      <td className="py-3 px-4 text-right font-semibold text-emerald-400">
                        {ds.row_count.toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <button
                            onClick={() => handlePreview(ds.id)}
                            className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-emerald-400 transition"
                            title="Pratinjau 20 baris"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(ds.id, ds.name)}
                            className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-rose-400 transition"
                            title="Hapus dari HDFS"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Preview Modal / Drawer */}
        {previewData && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <div>
                <h3 className="font-semibold text-slate-200 flex items-center gap-2">
                  <Eye className="w-5 h-5 text-emerald-400" />
                  Pratinjau Data: {previewData.name}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Menampilkan 20 baris pertama dari total {previewData.total_rows.toLocaleString()} baris
                </p>
              </div>
              <button
                onClick={() => setPreviewData(null)}
                className="text-xs px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
              >
                Tutup Pratinjau
              </button>
            </div>

            <div className="overflow-x-auto max-h-96 border border-slate-800 rounded-lg">
              <table className="w-full text-left text-xs font-mono text-slate-300">
                <thead className="bg-slate-950 text-slate-400 sticky top-0 border-b border-slate-800">
                  <tr>
                    {previewData.columns.map((col, idx) => (
                      <th key={idx} className="py-2.5 px-3 whitespace-nowrap">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {previewData.preview_rows.map((row, rIdx) => (
                    <tr key={rIdx} className="hover:bg-slate-800/40">
                      {previewData.columns.map((col, cIdx) => (
                        <td key={cIdx} className="py-2 px-3 whitespace-nowrap">
                          {String(row[col] ?? "")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Footer Attribution */}
        <footer className="text-center text-xs text-slate-500 py-6 border-t border-slate-900">
          Atribusi Sumber Data: NASA FIRMS (VIIRS & MODIS) | Copernicus ERA5 / Open-Meteo | CHIRPS UCSB |
          SIPONGI KEMENHUT | BNPB Indonesia. Platform Big Data Tugas Akhir.
        </footer>
      </div>
    </div>
  );
}
