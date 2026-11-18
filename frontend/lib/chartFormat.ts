/** Helper format khusus grafik analitik (tanpa dependensi React). */

export const MONTHS_SHORT = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "Mei",
  "Jun",
  "Jul",
  "Agu",
  "Sep",
  "Okt",
  "Nov",
  "Des",
];

export const CHART_COLORS = {
  fire: "#d9480f",
  fireRed: "#c92a2a",
  fireLight: "#f76707",
  neutral: "#adb5bd",
  neutralDark: "#868e96",
  teal: "#0b7285",
  axis: "#8f8279",
  grid: "#f0e8e0",
  text: "#1f1a17",
};

export const FONT_FAMILY = "Inter, ui-sans-serif, system-ui, sans-serif";

export function chartNumber(value: number): string {
  return new Intl.NumberFormat("id-ID").format(Math.round(value));
}

export function chartCompact(value: number): string {
  return new Intl.NumberFormat("id-ID", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

const dayFormatter = new Intl.DateTimeFormat("id-ID", {
  day: "numeric",
  month: "short",
  timeZone: "Asia/Jakarta",
});
const monthFormatter = new Intl.DateTimeFormat("id-ID", {
  month: "short",
  year: "numeric",
  timeZone: "Asia/Jakarta",
});

export function trendLabel(date: string, granularity: "day" | "week" | "month"): string {
  const parsed = new Date(`${date}T00:00:00+07:00`);
  if (Number.isNaN(parsed.getTime())) return date;
  if (granularity === "month") return monthFormatter.format(parsed);
  return dayFormatter.format(parsed);
}

export function fireAreaGradient() {
  return {
    type: "linear",
    x: 0,
    y: 0,
    x2: 0,
    y2: 1,
    colorStops: [
      { offset: 0, color: "rgba(217, 72, 15, 0.28)" },
      { offset: 1, color: "rgba(217, 72, 15, 0.02)" },
    ],
  };
}

export function heatColorStops() {
  return ["#fff4e6", "#ffd8bf", "#ffa94d", "#fd7e14", "#e8590c", "#c92a2a", "#7a0c1e"];
}
