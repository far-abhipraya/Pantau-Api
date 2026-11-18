/** Format angka, tanggal, dan label Bahasa Indonesia. */

const numberFormatter = new Intl.NumberFormat("id-ID");
const compactFormatter = new Intl.NumberFormat("id-ID", {
  notation: "compact",
  maximumFractionDigits: 1,
});
const dateFormatter = new Intl.DateTimeFormat("id-ID", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "Asia/Jakarta",
});
const timeFormatter = new Intl.DateTimeFormat("id-ID", {
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZone: "Asia/Jakarta",
});

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  return numberFormatter.format(value);
}

export function formatCompact(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  return compactFormatter.format(value);
}

export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return "–";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "–";
  return dateFormatter.format(date);
}

export function formatTimeWib(value: string | Date | null | undefined): string {
  if (!value) return "–";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "–";
  return `${timeFormatter.format(date).replaceAll(".", ":")} WIB`;
}

export function formatDateTimeWib(value: string | Date | null | undefined): string {
  if (!value) return "–";
  return `${formatDate(value)} · ${formatTimeWib(value)}`;
}

const CONFIDENCE_LABEL: Record<string, string> = {
  low: "Rendah",
  nominal: "Nominal",
  high: "Tinggi",
};

export function confidenceLabel(level: string): string {
  return CONFIDENCE_LABEL[level] ?? level;
}

export const CONFIDENCE_COLOR: Record<string, string> = {
  low: "#ffc078",
  nominal: "#f76707",
  high: "#b71c1c",
};

export function frpRadius(frp: number): number {
  if (!Number.isFinite(frp) || frp <= 0) return 3;
  return Math.min(9, 3 + Math.log2(frp + 1) * 1.35);
}

export function formatBytes(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  if (value < 1024) return `${value} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let size = value / 1024;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[unit]}`;
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || Number.isNaN(ms)) return "–";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)} s`;
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return `${minutes} m ${rest} s`;
}

export function formatJobDuration(startedAt: string | null, finishedAt: string | null): string {
  if (!startedAt) return "–";
  const start = new Date(startedAt).getTime();
  if (Number.isNaN(start)) return "–";
  const end = finishedAt ? new Date(finishedAt).getTime() : Date.now();
  if (Number.isNaN(end)) return "–";
  return formatDuration(Math.max(0, end - start));
}

export function formatRelativeAge(ageHours: number | null): string {
  if (ageHours === null) return "–";
  if (ageHours < 1) return "< 1 jam lalu";
  if (ageHours < 24) return `${Math.round(ageHours)} jam lalu`;
  return `${Math.round(ageHours / 24)} hari lalu`;
}
