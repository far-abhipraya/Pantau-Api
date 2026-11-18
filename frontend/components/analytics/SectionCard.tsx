"use client";

import clsx from "clsx";
import { AlertTriangle, Inbox } from "lucide-react";

/** Kerangka kartu grafik: judul, deskripsi, aksi, serta state loading/error/kosong. */

export default function SectionCard({
  id,
  title,
  description,
  actions,
  loading,
  error,
  empty,
  emptyHint,
  className,
  children,
  dark,
}: {
  id?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  emptyHint?: string;
  className?: string;
  children: React.ReactNode;
  dark?: boolean;
}) {
  return (
    <section
      id={id}
      className={clsx(
        "scroll-mt-36",
        dark ? "rounded-xl bg-ember text-ember-text" : "card",
        className,
      )}
      aria-busy={loading || undefined}
    >
      <div className="flex flex-wrap items-start justify-between gap-2 px-4 pt-4">
        <div className="min-w-0">
          <h3 className={clsx("font-display text-base font-semibold", dark ? "text-ember-text" : "text-text")}>
            {title}
          </h3>
          {description ? (
            <p className={clsx("mt-0.5 text-xs", dark ? "text-ember-text-muted" : "text-text-muted")}>
              {description}
            </p>
          ) : null}
        </div>
        {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
      </div>

      <div className="px-4 pb-4 pt-3">
        {loading ? (
          <div className="space-y-2" role="status" aria-label="Memuat grafik">
            <div className="h-3 w-2/3 animate-pulse rounded bg-surface-muted" />
            <div className="h-40 w-full animate-pulse rounded bg-surface-muted" />
          </div>
        ) : error ? (
          <div className="flex items-start gap-2 rounded-lg border border-[#FFC9C9] bg-[#FFF5F5] px-3 py-2 text-xs text-[#C92A2A]">
            <AlertTriangle className="mt-0.5 size-3.5 shrink-0" aria-hidden />
            <p>{error}</p>
          </div>
        ) : empty ? (
          <div className="flex flex-col items-center gap-1 rounded-lg border border-dashed border-border bg-surface-muted/50 px-4 py-8 text-center">
            <Inbox className="size-5 text-text-subtle" aria-hidden />
            <p className="text-sm font-medium text-text-muted">Belum ada data untuk filter ini</p>
            {emptyHint ? <p className="max-w-sm text-xs text-text-subtle">{emptyHint}</p> : null}
          </div>
        ) : (
          children
        )}
      </div>
    </section>
  );
}
