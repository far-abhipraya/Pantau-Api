"use client";

import clsx from "clsx";
import { ArrowDownRight, ArrowUpRight, Flame, MapPin, ShieldAlert } from "lucide-react";

import type { Kpi } from "@/lib/api";
import { formatNumber, formatRelativeAge } from "@/lib/format";

type Props = {
  kpi: Kpi | null;
  loading: boolean;
  error: string | null;
};

function MiniCard({
  label,
  value,
  hint,
  icon,
  loading,
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  icon: React.ReactNode;
  loading?: boolean;
}) {
  return (
    <div className="min-w-[132px] rounded-xl border border-border bg-surface/95 px-3 py-2.5 shadow-[var(--shadow-card)] backdrop-blur sm:min-w-[158px]">
      <div className="flex items-center gap-1.5 text-[11px] font-medium text-text-muted">
        {icon}
        <span className="truncate">{label}</span>
      </div>
      {loading ? (
        <div className="mt-1.5 h-7 w-20 animate-pulse rounded bg-surface-muted" />
      ) : (
        <p className="number mt-0.5 font-display text-2xl font-bold leading-8">{value}</p>
      )}
      {hint ? <div className="text-[11px] text-text-subtle">{hint}</div> : null}
    </div>
  );
}

export default function KpiCards({ kpi, loading, error }: Props) {
  const highShare =
    kpi && kpi.hotspots > 0 ? Math.round((kpi.high_confidence / kpi.hotspots) * 100) : 0;

  return (
    <div className="pointer-events-none absolute inset-x-3 top-20 z-[999] flex flex-col items-end gap-2 md:inset-x-auto md:right-3 md:top-20">
      {error ? (
        <div className="pointer-events-auto rounded-xl border border-danger/30 bg-surface px-3 py-2 text-xs text-danger shadow-[var(--shadow-card)]">
          KPI gagal dimuat: {error}
        </div>
      ) : null}
      <div className="pointer-events-auto flex w-full gap-2 overflow-x-auto pb-1 md:w-auto">
        <MiniCard
          label={`Hotspot (${kpi?.window_hours ?? 24} jam)`}
          icon={<Flame className="size-3.5 text-fire-deep-orange" aria-hidden />}
          value={formatNumber(kpi?.hotspots)}
          hint={
            kpi ? (
              <span className={clsx("flex items-center gap-1", kpi.freshness.status === "stale" && "text-warning")}>
                <span className="size-1.5 rounded-full bg-success" aria-hidden />
                {formatRelativeAge(kpi.freshness.age_hours)}
              </span>
            ) : null
          }
          loading={loading}
        />
        <MiniCard
          label="Provinsi tertinggi"
          icon={<MapPin className="size-3.5 text-fire-red" aria-hidden />}
          value={
            <span className="block max-w-[150px] truncate text-lg" title={kpi?.top_province?.name}>
              {kpi?.top_province?.name ?? "–"}
            </span>
          }
          hint={
            kpi?.top_province ? (
              <span className="flex items-center gap-1">
                <ArrowUpRight className="size-3" aria-hidden />
                {formatNumber(kpi.top_province.count)} hotspot
              </span>
            ) : null
          }
          loading={loading}
        />
        <MiniCard
          label="Confidence tinggi"
          icon={<ShieldAlert className="size-3.5 text-fire-crimson" aria-hidden />}
          value={formatNumber(kpi?.high_confidence)}
          hint={
            kpi ? (
              <span className="flex items-center gap-1">
                <ArrowDownRight className="size-3" aria-hidden />
                {highShare}% dari total
              </span>
            ) : null
          }
          loading={loading}
        />
      </div>
    </div>
  );
}
