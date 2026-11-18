"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, ShieldAlert } from "lucide-react";

import type { QuarantineResponse } from "@/lib/api";
import { formatBytes, formatDateTimeWib, formatNumber } from "@/lib/format";

export default function QuarantinePanel({
  data,
  loading,
  defaultOpen = false,
}: {
  data: QuarantineResponse | null;
  loading: boolean;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const count = data?.meta.count ?? 0;

  return (
    <section className="card overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 px-4 py-3 text-left"
      >
        <ShieldAlert className={`size-4 ${count > 0 ? "text-danger" : "text-text-subtle"}`} aria-hidden />
        <span className="font-display text-base font-semibold">Karantina</span>
        <span className="rounded-full bg-surface-muted px-2 py-0.5 text-[11px] text-text-muted">{count}</span>
        <span className="ml-auto text-text-muted">
          {open ? <ChevronUp className="size-4" aria-hidden /> : <ChevronDown className="size-4" aria-hidden />}
        </span>
      </button>

      {open ? (
        <div className="border-t border-border px-4 py-3">
          {loading && !data ? (
            <p className="text-xs text-text-muted">Memuat…</p>
          ) : count === 0 ? (
            <p className="text-xs text-text-muted">
              Tidak ada file gagal parse. Folder karantina:{" "}
              <code className="font-mono">{data?.meta.failed_dir ?? "–"}</code>
            </p>
          ) : (
            <ul className="divide-y divide-border/70">
              {data?.items.map((item) => (
                <li key={item.id} className="flex items-start justify-between gap-3 py-2">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium" title={item.file_name}>
                      {item.file_name}
                    </p>
                    <p className="text-[11px] text-text-muted">{item.reason}</p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="number text-xs">{formatNumber(item.row_count)} baris</p>
                    <p className="text-[10px] text-text-subtle">{formatDateTimeWib(item.created_at)}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}

          {data && data.meta.files.length > 0 ? (
            <div className="mt-3 rounded-lg bg-surface-muted px-3 py-2">
              <p className="text-[11px] font-medium text-text-muted">File di folder failed</p>
              <ul className="mt-1 space-y-0.5">
                {data.meta.files.slice(0, 5).map((file) => (
                  <li key={file.name} className="flex justify-between font-mono text-[10px] text-text-subtle">
                    <span className="truncate">{file.name}</span>
                    <span>{formatBytes(file.size_bytes)}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
