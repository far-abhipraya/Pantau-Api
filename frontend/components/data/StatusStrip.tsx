"use client";

import { Database, HardDriveDownload, ShieldAlert, Zap } from "lucide-react";

import type { SourcesResponse } from "@/lib/api";
import { formatCompact, formatDateTimeWib, formatNumber } from "@/lib/format";
import { Badge } from "@/components/ui/Badge";

function Card({
  icon,
  label,
  primary,
  secondary,
  progress,
  action,
  loading,
}: {
  icon: React.ReactNode;
  label: string;
  primary: React.ReactNode;
  secondary?: React.ReactNode;
  progress?: number;
  action?: React.ReactNode;
  loading?: boolean;
}) {
  return (
    <div className="card flex flex-col gap-1 p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-text-subtle">
          {icon}
          {label}
        </span>
        {action}
      </div>
      {loading ? (
        <div className="mt-1 h-8 w-28 animate-pulse rounded bg-surface-muted" />
      ) : (
        <p className="number font-display text-2xl font-bold leading-8">{primary}</p>
      )}
      {secondary ? <div className="text-[11px] text-text-muted">{secondary}</div> : null}
      {typeof progress === "number" ? (
        <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-surface-muted" role="presentation">
          <div
            className="h-full rounded-full bg-fire-deep-orange transition-[width] duration-300"
            style={{ width: `${Math.min(100, progress)}%` }}
          />
        </div>
      ) : null}
    </div>
  );
}

export default function StatusStrip({
  sources,
  loading,
  onOpenQuarantine,
}: {
  sources: SourcesResponse | null;
  loading: boolean;
  onOpenQuarantine: () => void;
}) {
  const strip = sources?.strip;
  const progress = sources
    ? Math.min(100, (sources.strip.total_raw_rows / sources.strip.target_rows) * 100)
    : 0;
  const sparkRunning = strip?.spark.status === "running";

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Card
        icon={<Database className="size-3.5 text-fire-deep-orange" aria-hidden />}
        label="Total baris mentah HDFS"
        primary={formatNumber(strip?.total_raw_rows ?? null)}
        secondary={
          <span className="flex items-center gap-2">
            <span>Target {formatCompact(strip?.target_rows ?? 1_000_000)}</span>
            {strip?.indicator_met ? <Badge tone="success">Terpenuhi</Badge> : <Badge tone="warning">Kurang</Badge>}
          </span>
        }
        progress={progress}
        loading={loading}
      />
      <Card
        icon={<HardDriveDownload className="size-3.5 text-fire-deep-orange" aria-hidden />}
        label="Ingest terakhir"
        primary={formatDateTimeWib(strip?.last_ingest.at ?? null)}
        secondary={
          strip?.last_ingest.source
            ? `${strip.last_ingest.source} · ${formatNumber(strip.last_ingest.rows)} baris · ${strip.last_ingest.status}`
            : "Belum ada catatan ingest"
        }
        loading={loading}
      />
      <Card
        icon={<Zap className={`size-3.5 ${sparkRunning ? "text-info" : "text-text-subtle"}`} aria-hidden />}
        label="Status Spark"
        primary={sparkRunning ? "Berjalan" : "Idle"}
        secondary={
          sparkRunning
            ? `${strip?.spark.active_type ?? ""} · ${strip?.spark.active_job ?? ""}`
            : `Driver ${formatCompact(strip?.hdfs_raw.files ?? 0)} file mentah`
        }
        loading={loading}
      />
      <Card
        icon={<ShieldAlert className={`size-3.5 ${(strip?.quarantine_count ?? 0) > 0 ? "text-danger" : "text-text-subtle"}`} aria-hidden />}
        label="Karantina"
        primary={formatNumber(strip?.quarantine_count ?? 0)}
        secondary={
          <button type="button" onClick={onOpenQuarantine} className="text-fire-deep-orange hover:underline">
            Lihat panel karantina
          </button>
        }
        loading={loading}
      />
    </div>
  );
}
