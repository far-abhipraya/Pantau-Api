import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Analitik · PantauApi",
  description:
    "Insight hotspot karhutla Indonesia: ringkasan KPI, tren, ranking wilayah, pola musiman, dan insight otomatis dari serving layer.",
};

export default function AnalyticsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
