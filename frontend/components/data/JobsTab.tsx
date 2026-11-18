"use client";

import { useCallback, useEffect, useState } from "react";
import { Cpu, RefreshCw } from "lucide-react";

import Drawer from "@/components/ui/Drawer";
import { Badge, StatusBadge } from "@/components/ui/Badge";
import { api, type JobDetail, type JobItem, type JobsResponse } from "@/lib/api";
import { formatDateTimeWib, formatJobDuration, formatNumber } from "@/lib/format";

const TYPE_LABEL: Record<string, string> = {
  PREPROCESSING: "Pre-processing",
  PROFILING: "Profiling",
  AGGREGATION: "Agregasi serving",
  INGEST_MANUAL: "Ingest manual",
  INGEST_FOLDER: "Impor folder",
  FEATURES: "Fitur ML",
  ML_TRAIN: "Latih model",
  ML_PREDICT: "Prediksi",
  ML_REFRESH: "Fitur + latih + prediksi",
};

export default function JobsTab({
  jobs,
  loading,
  onRefresh,
}: {
  jobs: JobsResponse | null;
  loading: boolean;
  onRefresh: () => void;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<JobDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  const loadDetail = useCallback(async (jobId: string) => {
    try {
      const data = await api.job(jobId);
      setDetail(data);
      setDetailError(null);
      return data;
    } catch (error) {
      setDetailError((error as Error).message);
      return null;
    }
  }, []);

  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    let timer: ReturnType<typeof setInterval> | null = null;
    const start = async () => {
      const data = await loadDetail(selected);
      if (cancelled || !data) return;
      if (data.status === "running" || data.status === "queued") {
        timer = setInterval(async () => {
          const next = await loadDetail(selected);
          if (!cancelled && next && next.status !== "running" && next.status !== "queued" && timer) {
            clearInterval(timer);
            onRefresh();
          }
        }, 3000);
      }
    };
    void start();
    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
  }, [selected, loadDetail, onRefresh]);

  const queue = jobs?.meta.queue;

  return (
    <div className="space-y-4">
      <div className="card flex flex-wrap items-center gap-3 px-4 py-3">
        <Cpu className="size-4 text-fire-deep-orange" aria-hidden />
        <div className="mr-auto">
          <p className="text-sm font-semibold">
            {queue?.running ? "Job Spark berjalan" : "Tidak ada job Spark berjalan"}
          </p>
          <p className="font-mono text-[11px] text-text-muted">
            {queue?.running ?? "idle"}
            {queue && queue.queued.length > 0 ? ` · antrean: ${queue.queued.join(", ")}` : ""}
          </p>
        </div>
        <Badge tone="muted">driver {jobs?.meta.driver_memory ?? "–"}</Badge>
        <Badge tone={(jobs?.meta.available_gb ?? 0) < 2 ? "warning" : "neutral"}>
          RAM bebas {jobs?.meta.available_gb ?? "–"} GB
        </Badge>
        <button
          type="button"
          onClick={onRefresh}
          className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border px-3 text-xs font-medium text-text-muted transition-colors hover:bg-surface-muted"
        >
          <RefreshCw className="size-3.5" aria-hidden /> Muat ulang
        </button>
      </div>

      <section className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px] text-left text-sm">
            <thead className="bg-surface-muted text-[11px] uppercase tracking-[0.06em] text-text-subtle">
              <tr>
                <th className="px-4 py-2 font-semibold">Jenis</th>
                <th className="px-3 py-2 font-semibold">Status</th>
                <th className="px-3 py-2 font-semibold">Mulai</th>
                <th className="px-3 py-2 text-right font-semibold">Durasi</th>
                <th className="px-3 py-2 text-right font-semibold">Baris in</th>
                <th className="px-3 py-2 text-right font-semibold">Baris out</th>
                <th className="px-4 py-2 font-semibold">Job ID</th>
              </tr>
            </thead>
            <tbody>
              {loading && !jobs ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-text-muted">
                    Memuat riwayat job…
                  </td>
                </tr>
              ) : (jobs?.items.length ?? 0) === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-text-muted">
                    Belum ada job.
                  </td>
                </tr>
              ) : (
                jobs?.items.map((job: JobItem) => (
                  <tr
                    key={job.id}
                    onClick={() => {
                      setDetail(null);
                      setSelected(job.id);
                    }}
                    className="cursor-pointer border-t border-border/70 transition-colors hover:bg-surface-muted/60"
                  >
                    <td className="px-4 py-2">{TYPE_LABEL[job.job_type] ?? job.job_type}</td>
                    <td className="px-3 py-2">
                      <StatusBadge status={job.status} />
                    </td>
                    <td className="px-3 py-2 text-xs text-text-muted">{formatDateTimeWib(job.started_at)}</td>
                    <td className="number px-3 py-2 text-right text-xs">
                      {formatJobDuration(job.started_at, job.finished_at)}
                    </td>
                    <td className="number px-3 py-2 text-right text-xs">{formatNumber(job.rows_in)}</td>
                    <td className="number px-3 py-2 text-right text-xs">{formatNumber(job.rows_out)}</td>
                    <td className="px-4 py-2 font-mono text-[10px] text-text-subtle">{job.id}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <Drawer
        open={selected !== null}
        title={detail ? (TYPE_LABEL[detail.job_type] ?? detail.job_type) : "Detail job"}
        subtitle={
          detail ? (
            <span className="flex items-center gap-2">
              <StatusBadge status={detail.status} />
              <span className="font-mono text-[10px]">{detail.id}</span>
            </span>
          ) : null
        }
        onClose={() => {
          setSelected(null);
          setDetail(null);
        }}
      >
        {detailError ? (
          <p className="text-sm text-danger">{detailError}</p>
        ) : !detail ? (
          <p className="text-sm text-text-muted">Memuat detail job…</p>
        ) : (
          <div className="space-y-4">
            <dl className="grid grid-cols-2 gap-2 text-xs">
              <div className="rounded-lg bg-surface-muted px-3 py-2">
                <dt className="text-[11px] text-text-muted">Mulai</dt>
                <dd>{formatDateTimeWib(detail.started_at)}</dd>
              </div>
              <div className="rounded-lg bg-surface-muted px-3 py-2">
                <dt className="text-[11px] text-text-muted">Selesai</dt>
                <dd>{formatDateTimeWib(detail.finished_at)}</dd>
              </div>
              <div className="rounded-lg bg-surface-muted px-3 py-2">
                <dt className="text-[11px] text-text-muted">Baris masuk</dt>
                <dd className="number">{formatNumber(detail.rows_in)}</dd>
              </div>
              <div className="rounded-lg bg-surface-muted px-3 py-2">
                <dt className="text-[11px] text-text-muted">Baris keluar</dt>
                <dd className="number">{formatNumber(detail.rows_out)}</dd>
              </div>
            </dl>

            <div>
              <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-text-subtle">
                Laporan
              </p>
              <pre className="max-h-64 overflow-auto rounded-lg bg-ember px-3 py-2 font-mono text-[10px] text-ember-text">
                {JSON.stringify(detail.report, null, 2)}
              </pre>
            </div>

            <div>
              <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-text-subtle">
                Log ringkas (ekor)
              </p>
              <pre className="max-h-72 overflow-auto rounded-lg border border-border bg-surface-muted px-3 py-2 font-mono text-[10px] text-text-muted">
                {detail.log_tail?.trim() ? detail.log_tail : "(belum ada log)"}
              </pre>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}
