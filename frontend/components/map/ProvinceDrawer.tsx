"use client";

import Link from "next/link";
import { X } from "lucide-react";

import type { ProvinceSummary } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import Sparkline from "@/components/Sparkline";

type Props = {
  province: string | null;
  summary: ProvinceSummary | null;
  loading: boolean;
  onClose: () => void;
};

export default function ProvinceDrawer({ province, summary, loading, onClose }: Props) {
  if (!province) return null;

  const trend = summary?.trend.map((point) => point.count) ?? [];
  const delta =
    summary && summary.previous_window > 0
      ? Math.round(((summary.last_window - summary.previous_window) / summary.previous_window) * 100)
      : null;

  return (
    <aside
      aria-label={`Ringkasan provinsi ${province}`}
      className="absolute inset-x-0 bottom-0 z-[1100] max-h-[70dvh] overflow-y-auto rounded-t-2xl border border-border bg-surface p-4 shadow-[var(--shadow-floating)] md:inset-x-auto md:right-3 md:top-20 md:max-h-[calc(100dvh-8rem)] md:w-[360px] md:rounded-2xl"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="field-label">Ringkasan provinsi</p>
          <h2 className="font-display text-xl font-bold leading-7">{province}</h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Tutup ringkasan provinsi"
          className="rounded-md p-1 text-text-muted hover:bg-surface-muted"
        >
          <X className="size-5" aria-hidden />
        </button>
      </div>

      {loading ? (
        <div className="mt-4 space-y-2">
          <div className="h-16 animate-pulse rounded-lg bg-surface-muted" />
          <div className="h-24 animate-pulse rounded-lg bg-surface-muted" />
        </div>
      ) : summary ? (
        <div className="mt-4 space-y-4">
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-lg bg-surface-muted px-3 py-2">
              <p className="text-[11px] text-text-muted">24 jam</p>
              <p className="number font-display text-xl font-bold">{formatNumber(summary.last_window)}</p>
              {delta !== null ? (
                <p className={delta >= 0 ? "text-[11px] text-danger" : "text-[11px] text-success"}>
                  {delta >= 0 ? "+" : ""}
                  {delta}% vs periode sebelumnya
                </p>
              ) : null}
            </div>
            <div className="rounded-lg bg-surface-muted px-3 py-2">
              <p className="text-[11px] text-text-muted">7 hari</p>
              <p className="number font-display text-xl font-bold">{formatNumber(summary.last_7d)}</p>
              <p className="text-[11px] text-text-subtle">Peringkat #{summary.rank} nasional</p>
            </div>
          </div>

          <div>
            <div className="mb-1 flex items-center justify-between">
              <p className="text-[11px] font-medium text-text-muted">Tren 7 hari</p>
              <p className="text-[11px] text-text-subtle">
                confidence tinggi 24 jam: {formatNumber(summary.high_last_window)}
              </p>
            </div>
            <Sparkline values={trend} />
            <div className="mt-1 flex justify-between text-[10px] text-text-subtle">
              {summary.trend.length > 0 ? (
                <>
                  <span>{summary.trend[0].date.slice(5)}</span>
                  <span>{summary.trend[summary.trend.length - 1].date.slice(5)}</span>
                </>
              ) : null}
            </div>
          </div>

          <Link
            href={`/analytics?province=${encodeURIComponent(province)}`}
            className="flex h-10 items-center justify-center rounded-lg bg-fire-deep-orange text-sm font-semibold text-white transition-colors hover:bg-fire-crimson"
          >
            Lihat analitik provinsi
          </Link>
        </div>
      ) : (
        <p className="mt-4 text-sm text-text-muted">Belum ada ringkasan untuk provinsi ini pada filter aktif.</p>
      )}
    </aside>
  );
}
