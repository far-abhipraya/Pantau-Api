"use client";

import { Flame, TrendingDown, TrendingUp } from "lucide-react";

import type { AnalyticsKpi } from "@/lib/api";
import { formatDate, formatDateTimeWib, formatNumber } from "@/lib/format";

function pctDelta(current: number, previous: number): number | null {
  if (!previous) return null;
  return ((current - previous) / previous) * 100;
}

function Delta({ value, suffix }: { value: number | null; suffix: string }) {
  if (value === null || !Number.isFinite(value)) {
    return <span className="text-[11px] text-ember-text-muted">tanpa pembanding</span>;
  }
  const up = value >= 0;
  return (
    <span className="flex items-center gap-1 text-[11px] text-ember-text-muted">
      {up ? (
        <TrendingUp className="size-3 text-[#ffa94d]" aria-hidden />
      ) : (
        <TrendingDown className="size-3 text-[#8ce99a]" aria-hidden />
      )}
      <span className="number font-medium text-ember-text">
        {up ? "+" : ""}
        {value.toLocaleString("id-ID", { maximumFractionDigits: 1 })}%
      </span>
      <span>{suffix}</span>
    </span>
  );
}

function Stat({
  label,
  value,
  detail,
  loading,
}: {
  label: string;
  value: React.ReactNode;
  detail: React.ReactNode;
  loading?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1 px-4 py-3 sm:px-5">
      <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ember-text-muted">
        {label}
      </span>
      {loading ? (
        <span className="mt-1 block h-8 w-24 animate-pulse rounded bg-white/10" />
      ) : (
        <span className="number font-display text-2xl font-bold leading-8 text-ember-text sm:text-3xl">
          {value}
        </span>
      )}
      <div className="min-h-4">{detail}</div>
    </div>
  );
}

export default function HeroKpi({
  kpi,
  loading,
  province,
}: {
  kpi: AnalyticsKpi | null;
  loading: boolean;
  province: string;
}) {
  const d7 = kpi ? pctDelta(kpi.last_7d, kpi.prev_7d) : null;
  const d30 = kpi ? pctDelta(kpi.last_30d, kpi.prev_30d) : null;
  const topShare =
    kpi?.top_province && kpi.last_30d
      ? (kpi.top_province.count / kpi.last_30d) * 100
      : null;

  return (
    <div className="overflow-hidden rounded-2xl bg-[linear-gradient(115deg,#2A1210_0%,#3B1814_55%,#4d1a11_100%)] text-ember-text shadow-[var(--shadow-floating)]">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 px-4 py-3 sm:px-5">
        <div className="flex items-center gap-2">
          <span className="flex size-6 items-center justify-center rounded-full bg-[linear-gradient(135deg,#F76707_0%,#C92A2A_100%)]">
            <Flame className="size-3.5 text-white" aria-hidden />
          </span>
          <h2 className="font-display text-sm font-semibold">Ringkasan hotspot</h2>
          <span className="rounded-full border border-white/15 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-ember-text-muted">
            Nasional
          </span>
        </div>
        <p className="text-[11px] text-ember-text-muted">
          {kpi?.meta.max_date
            ? `Data s.d. ${formatDate(kpi.meta.max_date)}`
            : "Memuat rentang data..."}
          {kpi?.meta.computed_at ? ` · dihitung ${formatDateTimeWib(kpi.meta.computed_at)}` : ""}
        </p>
      </div>

      {province ? (
        <p className="border-b border-white/10 bg-black/10 px-4 py-1.5 text-[11px] text-ember-text-muted sm:px-5">
          KPI hero selalu agregat nasional; filter <strong className="text-ember-text">{province}</strong>{" "}
          berlaku untuk seksi di bawahnya.
        </p>
      ) : null}

      <div className="grid grid-cols-1 divide-y divide-white/10 sm:grid-cols-2 sm:divide-y-0 lg:grid-cols-5 lg:divide-x">
        <Stat
          label="Hotspot hari ini"
          value={formatNumber(kpi?.today ?? null)}
          loading={loading}
          detail={
            kpi ? (
              <Delta
                value={
                  kpi.yesterday
                    ? ((kpi.today - kpi.yesterday) / kpi.yesterday) * 100
                    : null
                }
                suffix="vs kemarin"
              />
            ) : (
              <span className="text-[11px] text-ember-text-muted">memuat...</span>
            )
          }
        />
        <Stat
          label="7 hari terakhir"
          value={formatNumber(kpi?.last_7d ?? null)}
          loading={loading}
          detail={<Delta value={d7} suffix="vs 7 hari sebelumnya" />}
        />
        <Stat
          label="30 hari terakhir"
          value={formatNumber(kpi?.last_30d ?? null)}
          loading={loading}
          detail={<Delta value={d30} suffix="vs 30 hari sebelumnya" />}
        />
        <Stat
          label="Provinsi tertinggi"
          value={kpi?.top_province?.name ?? "—"}
          loading={loading}
          detail={
            kpi?.top_province ? (
              <span className="flex items-center gap-1 text-[11px] text-ember-text-muted">
                <span className="number font-medium text-ember-text">
                  {formatNumber(kpi.top_province.count)}
                </span>
                hotspot ·{" "}
                {topShare !== null
                  ? `${topShare.toLocaleString("id-ID", { maximumFractionDigits: 1 })}% dari 30 hari`
                  : "30 hari"}
              </span>
            ) : (
              <span className="text-[11px] text-ember-text-muted">tidak tersedia</span>
            )
          }
        />
        <Stat
          label="Rata-rata FRP"
          value={
            kpi
              ? kpi.avg_frp_30d.toLocaleString("id-ID", { maximumFractionDigits: 2 })
              : "—"
          }
          loading={loading}
          detail={
            kpi ? (
              <span className="flex items-center gap-1 text-[11px] text-ember-text-muted">
                <span className="number font-medium text-ember-text">
                  {formatNumber(kpi.high_confidence_30d)}
                </span>
                hotspot confidence tinggi (30 hari)
              </span>
            ) : (
              <span className="text-[11px] text-ember-text-muted">memuat...</span>
            )
          }
        />
      </div>
    </div>
  );
}
