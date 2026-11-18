"use client";

import { useMemo, useState } from "react";
import clsx from "clsx";

import SectionCard from "@/components/analytics/SectionCard";
import EChart from "@/components/charts/EChart";
import type { AnalyticsSeasonality } from "@/lib/api";
import { CHART_COLORS, FONT_FAMILY, chartNumber, heatColorStops } from "@/lib/chartFormat";

type Mode = "year" | "province";

function heatmapOption(
  rows: string[],
  columns: string[],
  values: Record<string, number[]>,
  axisLabelWidth: number,
) {
  const data: [number, number, number][] = [];
  rows.forEach((row, rowIndex) => {
    columns.forEach((_, columnIndex) => {
      data.push([columnIndex, rowIndex, values[row]?.[columnIndex] ?? 0]);
    });
  });
  const max = data.reduce((acc, item) => Math.max(acc, item[2]), 0);
  return {
    textStyle: { fontFamily: FONT_FAMILY },
    grid: { left: axisLabelWidth, right: 16, top: 8, bottom: 60 },
    tooltip: {
      trigger: "item",
      confine: true,
      formatter: (params: { value: [number, number, number] }) => {
        const [columnIndex, rowIndex, value] = params.value;
        return `<strong>${columns[columnIndex]} ${rows[rowIndex]}</strong><br/>Hotspot: ${chartNumber(value)}`;
      },
    },
    xAxis: {
      type: "category",
      data: columns,
      splitArea: { show: false },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: CHART_COLORS.grid } },
      axisLabel: { color: CHART_COLORS.axis, fontSize: 10 },
    },
    yAxis: {
      type: "category",
      data: rows,
      inverse: true,
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: CHART_COLORS.text, fontSize: 10 },
    },
    visualMap: {
      min: 0,
      max: Math.max(1, max),
      orient: "horizontal",
      left: "center",
      bottom: 0,
      itemWidth: 10,
      itemHeight: 70,
      text: ["Tinggi", "Rendah"],
      textStyle: { fontSize: 9, color: CHART_COLORS.axis },
      inRange: { color: heatColorStops() },
      calculable: false,
    },
    series: [
      {
        type: "heatmap",
        data,
        label: { show: false },
        itemStyle: { borderColor: "#ffffff", borderWidth: 1 },
        emphasis: {
          itemStyle: { borderColor: CHART_COLORS.text, borderWidth: 1 },
          label: { show: true, fontSize: 9, color: CHART_COLORS.text },
        },
      },
    ],
  };
}

export default function MusimanSection({
  data,
  loading,
  error,
}: {
  data: AnalyticsSeasonality | null;
  loading: boolean;
  error?: string | null;
}) {
  const [mode, setMode] = useState<Mode>("year");
  const provinceScoped = Boolean(data?.meta.province);
  const effectiveMode: Mode = provinceScoped ? "year" : mode;

  const yearOption = useMemo(() => {
    if (!data) return null;
    const years = data.years.map(String);
    return heatmapOption(years, data.months, data.by_year, 34);
  }, [data]);

  const provinceOption = useMemo(() => {
    if (!data) return null;
    const provinces = Object.keys(data.by_province);
    return heatmapOption(provinces, data.months, data.by_province, 132);
  }, [data]);

  const option = effectiveMode === "year" ? yearOption : provinceOption;

  return (
    <SectionCard
      id="musiman"
      title="Pola musiman"
      description={`Jumlah hotspot kumulatif per bulan · ${
        data?.meta.years_covered ? `riwayat ${data.meta.years_covered}` : "seluruh riwayat"
      }${data?.meta.province ? ` · ${data.meta.province}` : ""}.`}
      loading={loading && !data}
      error={error}
      empty={!loading && !data}
      emptyHint="Belum ada data musiman pada filter ini."
      actions={
        provinceScoped ? (
          <span className="rounded-full border border-border bg-surface-muted px-2.5 py-1 text-[11px] text-text-muted">
            {data?.meta.province}
          </span>
        ) : (
          <div className="inline-flex rounded-full border border-border bg-surface p-0.5" role="group" aria-label="Mode heatmap musiman">
            {(
              [
                { value: "year" as Mode, label: "Bulan × tahun" },
                { value: "province" as Mode, label: "Bulan × provinsi" },
              ] satisfies { value: Mode; label: string }[]
            ).map((item) => (
              <button
                key={item.value}
                type="button"
                onClick={() => setMode(item.value)}
                aria-pressed={mode === item.value}
                className={clsx(
                  "rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors duration-150",
                  mode === item.value
                    ? "bg-fire-tint text-fire-deep-orange"
                    : "text-text-muted hover:text-text",
                )}
              >
                {item.label}
              </button>
            ))}
          </div>
        )
      }
    >
      {option ? (
        <EChart
          option={option}
          height={effectiveMode === "year" ? 320 : 380}
          ariaLabel={`Heatmap hotspot ${effectiveMode === "year" ? "bulan per tahun" : "bulan per provinsi"}`}
        />
      ) : (
        <div className="h-72 animate-pulse rounded bg-surface-muted" />
      )}
      <p className="mt-2 text-[11px] text-text-subtle">
        {effectiveMode === "year"
          ? provinceScoped
            ? `Pola musiman ${data?.meta.province} per bulan dan tahun; skala kuning ke merah tua.`
            : "Setiap sel adalah total hotspot pada bulan tersebut di tahun terkait; skala kuning ke merah tua."
          : "10 provinsi teratas berdasarkan total hotspot sepanjang riwayat; skala kuning ke merah tua."}
      </p>
    </SectionCard>
  );
}
