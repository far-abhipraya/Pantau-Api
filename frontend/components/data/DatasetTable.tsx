"use client";

import { Eye, Loader2, RefreshCw, Trash2, Upload } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { DatasetItem, DatasetsResponse } from "@/lib/api";
import { formatBytes, formatDate, formatNumber } from "@/lib/format";

const ORIGIN_TONE: Record<string, "fire" | "info" | "muted"> = {
  manual: "fire",
  nifi: "info",
  auto: "info",
  histori: "muted",
};

const INGEST_LABEL: Record<string, string> = {
  manual: "Manual",
  nifi: "Otomatis (NiFi)",
  auto: "Otomatis",
  histori: "Histori",
};

export default function DatasetTable({
  data,
  loading,
  sourceFilter,
  onSourceFilter,
  onPreview,
  onDelete,
  onAddData,
  onImportFolder,
  importing,
  deletingId,
}: {
  data: DatasetsResponse | null;
  loading: boolean;
  sourceFilter: string;
  onSourceFilter: (source: string) => void;
  onPreview: (item: DatasetItem) => void;
  onDelete: (item: DatasetItem) => void;
  onAddData: () => void;
  onImportFolder: () => void;
  importing: boolean;
  deletingId: number | null;
}) {
  const items = data?.items ?? [];
  const sources = data?.meta.sources ?? [];

  return (
    <section className="card overflow-hidden">
      <header className="flex flex-wrap items-center gap-3 border-b border-border px-4 py-3">
        <div className="mr-auto">
          <h3 className="font-display text-base font-semibold">Dataset di HDFS</h3>
          <p className="text-[11px] text-text-muted">
            {formatNumber(data?.meta.summary.files ?? 0)} file ·{" "}
            {formatBytes(data?.meta.summary.total_size_bytes ?? 0)} · hanya di bawah{" "}
            <code className="font-mono">/karhutla</code>
          </p>
        </div>

        <label className="flex items-center gap-1.5 text-[11px] text-text-muted">
          Sumber
          <select
            value={sourceFilter}
            onChange={(event) => onSourceFilter(event.target.value)}
            className="h-8 rounded-lg border border-border bg-surface px-2 text-xs text-text"
          >
            <option value="">Semua</option>
            {sources.map((source) => (
              <option key={source} value={source}>
                {source}
              </option>
            ))}
          </select>
        </label>

        <button
          type="button"
          onClick={onImportFolder}
          disabled={importing}
          className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border px-3 text-xs font-medium text-text-muted transition-colors hover:bg-surface-muted disabled:opacity-60"
        >
          {importing ? <Loader2 className="size-3.5 animate-spin" aria-hidden /> : <RefreshCw className="size-3.5" aria-hidden />}
          Impor folder
        </button>

        {/* Tombol sekunder: tidak menonjol (FR-D3). */}
        <button
          type="button"
          onClick={onAddData}
          className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-fire-deep-orange/50 px-3 text-xs font-semibold text-fire-deep-orange transition-colors hover:bg-fire-tint"
        >
          <Upload className="size-3.5" aria-hidden />
          Tambah data
        </button>
      </header>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="bg-surface-muted text-[11px] uppercase tracking-[0.06em] text-text-subtle">
            <tr>
              <th className="px-4 py-2 font-semibold">Nama</th>
              <th className="px-3 py-2 font-semibold">Sumber</th>
              <th className="px-3 py-2 font-semibold">Jalur masuk</th>
              <th className="px-3 py-2 text-right font-semibold">Ukuran</th>
              <th className="px-3 py-2 text-right font-semibold">Baris</th>
              <th className="px-3 py-2 font-semibold">Tanggal</th>
              <th className="px-4 py-2 text-right font-semibold">Aksi</th>
            </tr>
          </thead>
          <tbody>
            {loading && items.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-text-muted">
                  Memuat daftar dataset…
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-text-muted">
                  Tidak ada file pada filter ini.
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={`${item.hdfs_path}`} className="border-t border-border/70 hover:bg-surface-muted/50">
                  <td className="max-w-[260px] px-4 py-2">
                    <p className="truncate font-medium" title={item.name}>
                      {item.name}
                    </p>
                    <p className="truncate font-mono text-[10px] text-text-subtle" title={item.hdfs_path}>
                      {item.hdfs_path}
                    </p>
                  </td>
                  <td className="px-3 py-2 text-xs text-text-muted">{item.source}</td>
                  <td className="px-3 py-2">
                    <Badge tone={ORIGIN_TONE[item.ingest_path] ?? "muted"}>
                      {INGEST_LABEL[item.ingest_path] ?? item.ingest_path}
                    </Badge>
                    {item.missing_in_hdfs ? (
                      <Badge tone="warning" className="ml-1">
                        Tak ada di HDFS
                      </Badge>
                    ) : null}
                  </td>
                  <td className="number px-3 py-2 text-right text-xs">{formatBytes(item.size_bytes)}</td>
                  <td className="number px-3 py-2 text-right text-xs">{formatNumber(item.row_count)}</td>
                  <td className="px-3 py-2 text-xs text-text-muted">
                    {item.created_at ? formatDate(item.created_at) : item.modified ?? "–"}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        type="button"
                        onClick={() => onPreview(item)}
                        disabled={!item.id}
                        aria-label={`Pratinjau ${item.name}`}
                        className="rounded-md p-1.5 text-text-muted transition-colors hover:bg-surface-muted hover:text-text disabled:opacity-40"
                      >
                        <Eye className="size-4" aria-hidden />
                      </button>
                      <button
                        type="button"
                        onClick={() => onDelete(item)}
                        disabled={!item.id || deletingId === item.id}
                        aria-label={`Hapus ${item.name}`}
                        className="rounded-md p-1.5 text-text-muted transition-colors hover:bg-[#FFF5F5] hover:text-danger disabled:opacity-40"
                      >
                        {deletingId === item.id ? (
                          <Loader2 className="size-4 animate-spin" aria-hidden />
                        ) : (
                          <Trash2 className="size-4" aria-hidden />
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
