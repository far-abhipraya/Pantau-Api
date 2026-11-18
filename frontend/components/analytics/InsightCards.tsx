"use client";

import clsx from "clsx";
import { Info, Sparkles } from "lucide-react";

import type { AnalyticsInsights, InsightCard } from "@/lib/api";
import { formatDateTimeWib, formatNumber } from "@/lib/format";

const CONFIDENCE_STYLE: Record<string, string> = {
  Tinggi: "border-[#FFC9C9] bg-[#FFF5F5] text-[#C92A2A]",
  Sedang: "border-[#FFE8A1] bg-[#FFF9DB] text-[#8A4B00]",
  Rendah: "border-border bg-surface-muted text-text-muted",
};

const EVIDENCE_LABEL: Record<string, string> = {
  recent_7d: "Hotspot 7 hari terakhir",
  prior_7d: "Hotspot 7 hari sebelumnya",
  top3: "Tiga provinsi teratas",
  total: "Total hotspot",
  share_percent: "Pangsa",
  peak_month: "Bulan puncak",
  peak_count: "Hotspot pada bulan puncak",
  n: "Ukuran sampel (n)",
  window: "Jendela perhitungan",
  computed_at: "Dihitung pada",
};

function evidenceValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (Array.isArray(value)) {
    return value
      .map((item) =>
        typeof item === "object" && item !== null
          ? `${(item as { province?: string }).province ?? ""} (${formatNumber(
              Number((item as { count?: number }).count ?? 0),
            )})`
          : String(item),
      )
      .join(", ");
  }
  if (typeof value === "object") return JSON.stringify(value);
  if (typeof value === "number") return formatNumber(value);
  return String(value);
}

function InsightTile({ card, highlight }: { card: InsightCard; highlight: boolean }) {
  return (
    <article
      className={clsx(
        "flex flex-col gap-2 rounded-xl border p-4",
        highlight
          ? "border-ember bg-[linear-gradient(135deg,#2A1210_0%,#3B1814_100%)] text-ember-text"
          : "border-border bg-surface shadow-[var(--shadow-card)]",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span
          className={clsx(
            "text-[10px] font-semibold uppercase tracking-[0.08em]",
            highlight ? "text-ember-text-muted" : "text-text-subtle",
          )}
        >
          {card.title}
        </span>
        <span
          className={clsx(
            "shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium",
            highlight ? "border-white/20 text-ember-text" : CONFIDENCE_STYLE[card.confidence],
          )}
        >
          Keyakinan: {card.confidence}
        </span>
      </div>

      <p
        className={clsx(
          "number font-display text-2xl font-bold leading-tight",
          highlight ? "text-ember-text" : "text-fire-deep-orange",
        )}
      >
        {card.key_figure}
      </p>

      <p className={clsx("text-xs leading-relaxed", highlight ? "text-ember-text-muted" : "text-text-muted")}>
        {card.sentence}
      </p>

      <details className="mt-auto pt-1 text-[11px]">
        <summary
          className={clsx(
            "cursor-pointer select-none font-medium",
            highlight ? "text-[#ffa94d]" : "text-fire-deep-orange",
          )}
        >
          Lihat bukti (n={formatNumber(Number(card.evidence.n ?? 0))})
        </summary>
        <dl className="mt-2 space-y-1">
          {Object.entries(card.evidence).map(([key, value]) => (
            <div key={key} className="flex gap-2 justify-between">
              <dt className={highlight ? "text-ember-text-muted" : "text-text-subtle"}>
                {EVIDENCE_LABEL[key] ?? key}
              </dt>
              <dd
                className={clsx(
                  "number text-right font-medium",
                  highlight ? "text-ember-text" : "text-text",
                )}
              >
                {key === "computed_at" ? formatDateTimeWib(String(value)) : evidenceValue(value)}
              </dd>
            </div>
          ))}
        </dl>
      </details>
    </article>
  );
}

export default function InsightCards({
  data,
  loading,
  error,
  periodLabel,
}: {
  data: AnalyticsInsights | null;
  loading: boolean;
  error?: string | null;
  periodLabel: string;
}) {
  return (
    <section aria-labelledby="insight-heading" className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 id="insight-heading" className="flex items-center gap-2 font-display text-lg font-bold">
            <Sparkles className="size-4 text-fire-deep-orange" aria-hidden />
            Insight utama
          </h2>
          <p className="mt-0.5 text-xs text-text-muted">
            Periode {periodLabel}
            {data?.meta.computed_at ? ` · dihitung ${formatDateTimeWib(data.meta.computed_at)}` : ""} ·
            semua kartu dihitung dari serving layer, bukan teks statis.
          </p>
        </div>
        {data?.meta.skipped.length ? (
          <details className="max-w-md text-[11px] text-text-muted">
            <summary className="flex cursor-pointer items-center gap-1 font-medium text-text-muted">
              <Info className="size-3.5" aria-hidden />
              {data.meta.skipped.length} kelompok insight belum dihitung
            </summary>
            <ul className="mt-1 list-disc space-y-0.5 pl-4">
              {data.meta.skipped.map((item) => (
                <li key={item.id}>
                  <span className="font-medium">{item.id}</span>: {item.reason}
                </li>
              ))}
            </ul>
          </details>
        ) : null}
      </div>

      {loading ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2].map((index) => (
            <div key={index} className="card h-40 animate-pulse" />
          ))}
        </div>
      ) : error ? (
        <div className="card border-[#FFC9C9] bg-[#FFF5F5] p-4 text-xs text-[#C92A2A]">{error}</div>
      ) : !data || data.cards.length === 0 ? (
        <div className="card p-6 text-sm text-text-muted">
          Belum ada insight yang memenuhi ambang minimum untuk filter ini. Coba perbesar rentang waktu.
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {data.cards.map((card, index) => (
            <InsightTile key={card.id} card={card} highlight={index === 0} />
          ))}
        </div>
      )}
    </section>
  );
}
