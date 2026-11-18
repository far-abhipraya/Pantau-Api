"use client";

import { useCallback, useEffect, useState } from "react";
import { CalendarClock, CloudSun, Flame, RefreshCw } from "lucide-react";

import DatasetTable from "@/components/data/DatasetTable";
import QuarantinePanel from "@/components/data/QuarantinePanel";
import Drawer from "@/components/ui/Drawer";
import { SourceStatusBadge } from "@/components/ui/Badge";
import {
  api,
  type DatasetItem,
  type DatasetPreview,
  type DatasetsResponse,
  type QuarantineResponse,
  type SourcesResponse,
} from "@/lib/api";
import { formatBytes, formatDate, formatNumber } from "@/lib/format";

function SourceCard({ source }: { source: SourcesResponse["sources"][number] }) {
  const weather = source.kind === "weather";
  return (
    <div className="card flex flex-col gap-2 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="flex size-7 items-center justify-center rounded-full bg-fire-tint">
            {weather ? (
              <CloudSun className="size-3.5 text-weather-teal" aria-hidden />
            ) : (
              <Flame className="size-3.5 text-fire-deep-orange" aria-hidden />
            )}
          </span>
          <p className="text-sm font-semibold leading-5">{source.name}</p>
        </div>
        <SourceStatusBadge status={source.status} />
      </div>

      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] text-text-muted">
        <dt>Pembaruan</dt>
        <dd className="text-right text-text">
          {source.last_update ? formatDate(source.last_update) : "–"}
        </dd>
        {weather ? (
          <>
            <dt>File</dt>
            <dd className="number text-right text-text">{formatNumber(source.files ?? 0)}</dd>
            <dt>Ukuran</dt>
            <dd className="number text-right text-text">{formatBytes(source.size_bytes ?? 0)}</dd>
          </>
        ) : (
          <>
            <dt>Baris bersih</dt>
            <dd className="number text-right text-text">{formatNumber(source.rows)}</dd>
            <dt>Rentang</dt>
            <dd className="text-right text-text">
              {source.date_range?.start ? `${formatDate(source.date_range.start)} – ${formatDate(source.date_range.end)}` : "–"}
            </dd>
          </>
        )}
      </dl>

      <p className="truncate font-mono text-[10px] text-text-subtle" title={source.hdfs_path}>
        {source.hdfs_path}
      </p>
      {weather && source.status === "kosong" ? (
        <p className="text-[11px] text-warning">Cuaca belum dipetakan ke pipeline (menunggu Fase 5).</p>
      ) : null}
    </div>
  );
}

export default function SourcesTab({
  sources,
  datasets,
  quarantine,
  loadingSources,
  loadingDatasets,
  loadingQuarantine,
  sourceFilter,
  onSourceFilter,
  onAddData,
  onImportFolder,
  importing,
  onDeleteDataset,
  deletingId,
  onRefresh,
}: {
  sources: SourcesResponse | null;
  datasets: DatasetsResponse | null;
  quarantine: QuarantineResponse | null;
  loadingSources: boolean;
  loadingDatasets: boolean;
  loadingQuarantine: boolean;
  sourceFilter: string;
  onSourceFilter: (source: string) => void;
  onAddData: () => void;
  onImportFolder: () => void;
  importing: boolean;
  onDeleteDataset: (item: DatasetItem) => void;
  deletingId: number | null;
  onRefresh: () => void;
}) {
  const [previewItem, setPreviewItem] = useState<DatasetItem | null>(null);
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const openPreview = useCallback((item: DatasetItem) => {
    setPreview(null);
    setPreviewError(null);
    setPreviewLoading(true);
    setPreviewItem(item);
  }, []);

  useEffect(() => {
    if (!previewItem?.id) return;
    const controller = new AbortController();
    api
      .datasetPreview(previewItem.id, 30, { signal: controller.signal })
      .then((data) => setPreview(data))
      .catch((error: unknown) => {
        if ((error as Error).name !== "AbortError") setPreviewError((error as Error).message);
      })
      .finally(() => setPreviewLoading(false));
    return () => controller.abort();
  }, [previewItem]);

  const schedule = sources?.schedule;

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {(sources?.sources ?? []).map((source) => (
          <SourceCard key={source.id} source={source} />
        ))}
        {loadingSources && !sources
          ? Array.from({ length: 3 }).map((_, index) => (
              <div key={index} className="card h-32 animate-pulse bg-surface-muted" />
            ))
          : null}
      </div>

      <section className="card p-4">
        <div className="flex items-center gap-2">
          <CalendarClock className="size-4 text-fire-deep-orange" aria-hidden />
          <h3 className="font-display text-base font-semibold">Jadwal akuisisi otomatis</h3>
        </div>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <div className="rounded-xl bg-surface-muted px-3 py-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">NiFi (NRT)</p>
              <span className="text-[11px] text-text-muted">tiap {schedule?.nifi.interval_hours ?? 3} jam</span>
            </div>
            <p className="mt-1 text-[11px] text-text-muted">
              Eksekusi berikutnya: {schedule?.nifi.next_run ? formatDate(schedule.nifi.next_run) : "belum aktif (Fase 7)"}
            </p>
            <p className="mt-1 text-[11px] text-text-subtle">{schedule?.nifi.note}</p>
            <a
              href={schedule?.nifi.url ?? "#"}
              target="_blank"
              rel="noreferrer"
              className="mt-1 inline-block font-mono text-[10px] text-fire-deep-orange hover:underline"
            >
              {schedule?.nifi.url}
            </a>
          </div>
          <div className="rounded-xl bg-surface-muted px-3 py-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">Impor folder</p>
              <span className="text-[11px] text-text-muted">
                {schedule?.folder_import.enabled
                  ? `tiap ${Math.round((schedule.folder_import.interval_seconds ?? 0) / 60)} menit`
                  : "nonaktif"}
              </span>
            </div>
            <p className="mt-1 text-[11px] text-text-muted">
              Berikutnya: {schedule?.folder_import.next_run ? formatDate(schedule.folder_import.next_run) : "–"}
            </p>
            <p className="mt-1 truncate font-mono text-[10px] text-text-subtle">{schedule?.folder_import.inbox}</p>
            <button
              type="button"
              onClick={onImportFolder}
              disabled={importing}
              className="mt-2 inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-surface px-3 text-xs font-medium text-text-muted transition-colors hover:bg-surface-muted disabled:opacity-60"
            >
              <RefreshCw className={`size-3.5 ${importing ? "animate-spin" : ""}`} aria-hidden />
              Impor sekarang
            </button>
          </div>
        </div>
      </section>

      <DatasetTable
        data={datasets}
        loading={loadingDatasets}
        sourceFilter={sourceFilter}
        onSourceFilter={onSourceFilter}
        onPreview={openPreview}
        onDelete={onDeleteDataset}
        onAddData={onAddData}
        onImportFolder={onImportFolder}
        importing={importing}
        deletingId={deletingId}
      />

      <div className="flex justify-end">
        <button
          type="button"
          onClick={onRefresh}
          className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border px-3 text-xs font-medium text-text-muted transition-colors hover:bg-surface-muted"
        >
          <RefreshCw className="size-3.5" aria-hidden /> Muat ulang katalog
        </button>
      </div>

      <QuarantinePanel data={quarantine} loading={loadingQuarantine} />

      <Drawer
        open={previewItem !== null}
        title={previewItem?.name ?? "Pratinjau"}
        subtitle={<span className="font-mono text-[11px]">{previewItem?.hdfs_path}</span>}
        onClose={() => {
          setPreviewItem(null);
          setPreview(null);
        }}
      >
        {previewLoading ? (
          <p className="text-sm text-text-muted">Memuat pratinjau…</p>
        ) : previewError ? (
          <p className="text-sm text-danger">{previewError}</p>
        ) : preview ? (
          <div className="space-y-3">
            <p className="text-xs text-text-muted">
              {preview.columns.length} kolom · menampilkan {preview.rows.length} baris pertama
              {preview.truncated ? " (terpotong)" : ""}
            </p>
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full min-w-[520px] text-left text-[11px]">
                <thead className="bg-surface-muted text-text-subtle">
                  <tr>
                    {preview.columns.map((column) => (
                      <th key={column} className="whitespace-nowrap px-2 py-1.5 font-semibold">
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.map((row, rowIndex) => (
                    <tr key={rowIndex} className="border-t border-border/60">
                      {row.map((cell, cellIndex) => (
                        <td key={cellIndex} className="whitespace-nowrap px-2 py-1 font-mono text-[10px]">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}
