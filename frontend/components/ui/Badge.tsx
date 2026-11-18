import clsx from "clsx";
import { CheckCircle2, Clock, Loader2, XCircle } from "lucide-react";

type Tone = "neutral" | "success" | "warning" | "danger" | "info" | "fire" | "muted";

const TONES: Record<Tone, string> = {
  neutral: "border-border bg-surface-muted text-text-muted",
  muted: "border-border bg-surface text-text-subtle",
  success: "border-[#B2F2BB] bg-[#EBFBEE] text-[#2B8A3E]",
  warning: "border-[#FFE8A1] bg-[#FFF9DB] text-[#8A4B00]",
  danger: "border-[#FFC9C9] bg-[#FFF5F5] text-[#C92A2A]",
  info: "border-[#A5D8FF] bg-[#E7F5FF] text-[#1864AB]",
  fire: "border-fire-tint-strong bg-fire-tint text-fire-deep-orange",
};

export function Badge({
  tone = "neutral",
  children,
  className,
  mono,
}: {
  tone?: Tone;
  children: React.ReactNode;
  className?: string;
  mono?: boolean;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium",
        TONES[tone],
        mono && "font-mono text-[10px]",
        className,
      )}
    >
      {children}
    </span>
  );
}

const STATUS_TONE: Record<string, Tone> = {
  queued: "neutral",
  running: "info",
  COMPLETED: "success",
  success: "success",
  FAILED: "danger",
  failed: "danger",
};

const STATUS_LABEL: Record<string, string> = {
  queued: "Menunggu",
  running: "Berjalan",
  COMPLETED: "Selesai",
  success: "Selesai",
  FAILED: "Gagal",
  failed: "Gagal",
};

export function StatusBadge({ status }: { status: string }) {
  const tone = STATUS_TONE[status] ?? "neutral";
  const icon =
    status === "running" ? (
      <Loader2 className="size-3 animate-spin" aria-hidden />
    ) : status === "queued" ? (
      <Clock className="size-3" aria-hidden />
    ) : tone === "success" ? (
      <CheckCircle2 className="size-3" aria-hidden />
    ) : tone === "danger" ? (
      <XCircle className="size-3" aria-hidden />
    ) : null;
  return (
    <Badge tone={tone}>
      {icon}
      {STATUS_LABEL[status] ?? status}
    </Badge>
  );
}

export function SourceStatusBadge({ status }: { status: string }) {
  if (status === "aktif") return <Badge tone="success">Aktif</Badge>;
  if (status === "tertunda") return <Badge tone="warning">Tertunda</Badge>;
  if (status === "gagal") return <Badge tone="danger">Gagal</Badge>;
  return <Badge tone="neutral">Kosong</Badge>;
}
