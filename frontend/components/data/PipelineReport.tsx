"use client";

import { ArrowRight } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { PreprocessReport, ProfilingReport } from "@/lib/api";
import { formatDateTimeWib, formatDuration, formatNumber } from "@/lib/format";

export function FunnelReport({ report }: { report: PreprocessReport }) {
  const funnel = report.funnel ?? [];
  const max = Math.max(1, ...funnel.map((step) => step.rows));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 text-[11px] text-text-muted">
        <span>Job {report.job_id}</span>
        <span>·</span>
        <span>Selesai {formatDateTimeWib(report.finished_at)}</span>
        <span>·</span>
        <span>
          Laju bersih <strong className="text-text">{report.rows.clean_rate_percent}%</strong>
        </span>
      </div>

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.08em] text-text-subtle">
          Funnel jumlah baris per langkah
        </p>
        <ul className="space-y-1.5">
          {funnel.map((step) => (
            <li key={step.step} className="flex items-center gap-3">
              <span className="w-44 shrink-0 truncate text-[11px] text-text-muted" title={step.label}>
                {step.label}
              </span>
              <span className="relative h-5 flex-1 overflow-hidden rounded bg-surface-muted">
                <span
                  className="absolute inset-y-0 left-0 rounded bg-fire-orange/80"
                  style={{ width: `${(step.rows / max) * 100}%` }}
                />
              </span>
              <span className="number w-24 shrink-0 text-right text-[11px] font-medium">
                {formatNumber(step.rows)}
              </span>
              <span className="number w-16 shrink-0 text-right text-[10px] text-text-subtle">
                {formatDuration(step.duration_ms)}
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-1 text-[10px] text-text-subtle">
          {funnel.map((step) => step.note).filter(Boolean).slice(0, 4).join(" · ")}
        </p>
      </div>

      <div className="grid gap-2 sm:grid-cols-3">
        <div className="rounded-lg bg-surface-muted px-3 py-2">
          <p className="text-[11px] text-text-muted">Duplikat dibuang</p>
          <p className="number font-display text-lg font-bold">{formatNumber(report.rows.duplicates_removed)}</p>
        </div>
        <div className="rounded-lg bg-surface-muted px-3 py-2">
          <p className="text-[11px] text-text-muted">Di luar bbox</p>
          <p className="number font-display text-lg font-bold">{formatNumber(report.rows.out_of_bbox)}</p>
        </div>
        <div className="rounded-lg bg-surface-muted px-3 py-2">
          <p className="text-[11px] text-text-muted">Koordinat/waktu tidak valid</p>
          <p className="number font-display text-lg font-bold">
            {formatNumber(report.rows.invalid_coords_or_time)}
          </p>
        </div>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        <div className="rounded-lg border border-border px-3 py-2">
          <p className="text-[11px] font-semibold text-text-muted">Normalisasi</p>
          <p className="mt-1 text-xs">
            Metode: <strong>{report.normalization?.method ?? "–"}</strong>
          </p>
          {report.normalization?.params ? (
            <ul className="mt-1 grid grid-cols-2 gap-x-3 font-mono text-[10px] text-text-subtle">
              {Object.entries(report.normalization.params)
                .filter(([, value]) => value !== null)
                .slice(0, 8)
                .map(([key, value]) => (
                  <li key={key} className="flex justify-between">
                    <span className="truncate">{key}</span>
                    <span>{value}</span>
                  </li>
                ))}
            </ul>
          ) : null}
        </div>
        <div className="rounded-lg border border-border px-3 py-2">
          <p className="text-[11px] font-semibold text-text-muted">Penanganan nilai kosong</p>
          <p className="mt-1 text-xs">
            Strategi: <strong>{report.null_handling?.strategy ?? "–"}</strong>
          </p>
          <ul className="mt-1 space-y-0.5 font-mono text-[10px] text-text-subtle">
            {Object.entries(report.null_handling?.filled ?? {}).map(([column, count]) => (
              <li key={column} className="flex justify-between">
                <span>{column}</span>
                <span>{formatNumber(count)} diisi</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {report.sensors && report.sensors.length > 0 ? (
        <div>
          <p className="mb-1 text-[11px] font-semibold text-text-muted">Sebaran sensor (baris bersih)</p>
          <div className="flex flex-wrap gap-1.5">
            {report.sensors.map((sensor) => (
              <Badge key={`${sensor.instrument}-${sensor.satellite}`} tone="fire">
                {sensor.instrument} · {sensor.satellite}: {formatNumber(sensor.count)}
              </Badge>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function ProfilingSummary({ report }: { report: ProfilingReport }) {
  const columns = report.columns ?? [];
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-lg bg-surface-muted px-3 py-2">
          <p className="text-[11px] text-text-muted">Baris</p>
          <p className="number font-display text-lg font-bold">{formatNumber(report.total_rows)}</p>
        </div>
        <div className="rounded-lg bg-surface-muted px-3 py-2">
          <p className="text-[11px] text-text-muted">Duplikat kunci</p>
          <p className="number font-display text-lg font-bold">
            {formatNumber(report.duplicate_rows_on_key ?? 0)}
          </p>
        </div>
        <div className="rounded-lg bg-surface-muted px-3 py-2">
          <p className="text-[11px] text-text-muted">Rentang tanggal</p>
          <p className="text-xs font-medium">
            {report.date_range.start} → {report.date_range.end}
          </p>
        </div>
        <div className="rounded-lg bg-surface-muted px-3 py-2">
          <p className="text-[11px] text-text-muted">FRP rata-rata</p>
          <p className="number text-xs font-medium">{report.frp_metrics.avg} MW</p>
        </div>
      </div>

      {columns.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full min-w-[320px] text-left text-[11px]">
            <thead className="bg-surface-muted text-text-subtle">
              <tr>
                <th className="px-2 py-1.5 font-semibold">Kolom</th>
                <th className="px-2 py-1.5 font-semibold">Tipe</th>
                <th className="px-2 py-1.5 text-right font-semibold">Null %</th>
                <th className="px-2 py-1.5 text-right font-semibold">Unik</th>
              </tr>
            </thead>
            <tbody>
              {columns.map((column) => (
                <tr key={column.name} className="border-t border-border/60">
                  <td className="px-2 py-1 font-mono text-[10px]">{column.name}</td>
                  <td className="px-2 py-1 text-text-muted">{column.dtype}</td>
                  <td className="number px-2 py-1 text-right">{column.null_percent}</td>
                  <td className="number px-2 py-1 text-right">{formatNumber(column.distinct)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {report.distribution_deciles ? (
        <div className="space-y-1">
          {Object.entries(report.distribution_deciles).map(([metric, values]) => (
            <div key={metric}>
              <p className="text-[11px] font-semibold text-text-muted">Desil {metric}</p>
              <p className="font-mono text-[10px] text-text-subtle">{values.join(" · ")}</p>
            </div>
          ))}
        </div>
      ) : null}

      <p className="flex items-center gap-1 text-[10px] text-text-subtle">
        Profil dihitung dari data mentah <ArrowRight className="size-3" aria-hidden /> lihat funnel setelah pipeline.
      </p>
    </div>
  );
}
