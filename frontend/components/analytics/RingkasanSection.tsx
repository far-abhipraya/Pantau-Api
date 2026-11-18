"use client";

import { useMemo, useState } from "react";
import clsx from "clsx";

import SectionCard from "@/components/analytics/SectionCard";
import EChart from "@/components/charts/EChart";
import type { AnalyticsGranularity, AnalyticsTrend, AnalyticsYearCompare } from "@/lib/api";
import {
  CHART_COLORS,
  FONT_FAMILY,
  chartCompact,
  chartNumber,
  fireAreaGradient,
  trendLabel,
} from "@/lib/chartFormat";

const GRANULARITY_LABEL: Record<AnalyticsGranularity, string> = {
  day: "Harian",
  week: "Mingguan",
  month: "Bulanan",
};

const DOY_MONTHS: Record<number, string> = {
  1: "Jan",
  32: "Feb",
  60: "Mar",
  91: "Apr",
  121: "Mei",
  152: "Jun",
  182: "Jul",
  213: "Agu",
  244: "Sep",
  274: "Okt",
  305: "Nov",
  335: "Des",
};

export default function RingkasanSection({
  trend,
  yearCompare,
  loading,
  trendError,
  yearError,
  granularity,
  onGranularityChange,
}: {
  trend: AnalyticsTrend | null;
  yearCompare: AnalyticsYearCompare | null;
  loading: boolean;
  trendError?: string | null;
  yearError?: string | null;
  granularity: AnalyticsGranularity;
  onGranularityChange: (value: AnalyticsGranularity) => void;
}) {
  const [showHigh, setShowHigh] = useState(false);

  const trendOption = useMemo(() => {
    const points = trend?.points ?? [];
    return {
      textStyle: { fontFamily: FONT_FAMILY },
      grid: { left: 12, right: 16, top: 24, bottom: 8, containLabel: true },
      tooltip: {
        trigger: "axis",
        confine: true,
        formatter: (params: unknown) => {
          const list = params as { axisValue: string; dataIndex: number }[];
          const index = list[0]?.dataIndex ?? 0;
          const point = points[index];
          if (!point) return "";
          return [
            `<strong>${list[0]?.axisValue ?? point.date}</strong>`,
            `Hotspot: ${chartNumber(point.count)}`,
            `Confidence tinggi: ${chartNumber(point.high_count)}`,
          ].join("<br/>");
        },
      },
      xAxis: {
        type: "category",
        data: points.map((point) => trendLabel(point.date, granularity)),
        boundaryGap: false,
        axisLine: { lineStyle: { color: CHART_COLORS.grid } },
        axisTick: { show: false },
        axisLabel: { color: CHART_COLORS.axis, fontSize: 10, hideOverlap: true },
      },
      yAxis: {
        type: "value",
        splitLine: { lineStyle: { color: CHART_COLORS.grid } },
        axisLabel: { color: CHART_COLORS.axis, fontSize: 10, formatter: (value: number) => chartCompact(value) },
      },
      series: [
        {
          name: "Hotspot",
          type: "line",
          smooth: true,
          symbol: "none",
          lineStyle: { width: 2, color: CHART_COLORS.fire },
          itemStyle: { color: CHART_COLORS.fire },
          areaStyle: { color: fireAreaGradient() },
          data: points.map((point) => point.count),
        },
        ...(showHigh
          ? [
              {
                name: "Confidence tinggi",
                type: "line",
                smooth: true,
                symbol: "none",
                lineStyle: { width: 1.5, color: CHART_COLORS.fireRed, type: "dashed" },
                itemStyle: { color: CHART_COLORS.fireRed },
                data: points.map((point) => point.high_count),
              },
            ]
          : []),
      ],
    };
  }, [trend, granularity, showHigh]);

  const yearOption = useMemo(() => {
    const years = yearCompare?.years ?? [];
    const current = yearCompare?.current_year;
    const mean = yearCompare?.historical_mean ?? [];
    const past = years.filter((item) => item.year !== current);
    return {
      textStyle: { fontFamily: FONT_FAMILY },
      grid: { left: 12, right: 16, top: 28, bottom: 8, containLabel: true },
      legend: {
        top: 0,
        type: "scroll",
        textStyle: { fontSize: 10, color: CHART_COLORS.axis },
        itemWidth: 12,
        itemHeight: 8,
      },
      tooltip: {
        trigger: "axis",
        confine: true,
        formatter: (params: unknown) => {
          const list = params as { seriesName: string; value: [number, number] }[];
          if (!list.length) return "";
          const doy = list[0].value[0];
          return [
            `<strong>Hari ke-${doy} dalam tahun</strong>`,
            ...list.map((item) => `${item.seriesName}: ${chartNumber(item.value[1])}`),
          ].join("<br/>");
        },
      },
      xAxis: {
        type: "value",
        min: 1,
        max: 366,
        splitLine: { show: false },
        axisLine: { lineStyle: { color: CHART_COLORS.grid } },
        axisTick: { show: false },
        axisLabel: {
          color: CHART_COLORS.axis,
          fontSize: 10,
          formatter: (value: number) => DOY_MONTHS[value] ?? "",
        },
      },
      yAxis: {
        type: "value",
        splitLine: { lineStyle: { color: CHART_COLORS.grid } },
        axisLabel: { color: CHART_COLORS.axis, fontSize: 10, formatter: (value: number) => chartCompact(value) },
      },
      series: [
        ...past.map((item) => ({
          name: String(item.year),
          type: "line",
          symbol: "none",
          smooth: false,
          lineStyle: { width: 1, color: CHART_COLORS.neutral },
          itemStyle: { color: CHART_COLORS.neutral },
          emphasis: { disabled: true },
          data: item.points.map((point) => [point.doy, point.cum]),
        })),
        ...(mean.length
          ? [
              {
                name: "Rata-rata historis",
                type: "line",
                symbol: "none",
                smooth: false,
                lineStyle: { width: 1.5, color: CHART_COLORS.neutralDark, type: "dashed" },
                itemStyle: { color: CHART_COLORS.neutralDark },
                data: mean.map((point) => [point.doy, point.cum]),
              },
            ]
          : []),
        ...years
          .filter((item) => item.year === current)
          .map((item) => ({
            name: `${item.year} (tahun berjalan)`,
            type: "line",
            symbol: "none",
            smooth: false,
            lineStyle: { width: 2.5, color: CHART_COLORS.fireRed },
            itemStyle: { color: CHART_COLORS.fireRed },
            z: 5,
            data: item.points.map((point) => [point.doy, point.cum]),
          })),
      ],
    };
  }, [yearCompare]);

  const trendEmpty = (trend?.points.length ?? 0) === 0;
  const yearEmpty = (yearCompare?.years.length ?? 0) === 0;

  return (
    <div className="space-y-3">
      <SectionCard
        id="ringkasan"
        title="Tren hotspot"
        description={`Jumlah hotspot per ${granularity === "day" ? "hari" : granularity === "week" ? "minggu" : "bulan"} dari serving layer.`}
        loading={loading && !trend}
        error={trendError}
        empty={!loading && trendEmpty}
        emptyHint="Rentang atau filter ini tidak memiliki baris agregat."
        actions={
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowHigh((value) => !value)}
              aria-pressed={showHigh}
              className={clsx(
                "rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors duration-150",
                showHigh
                  ? "border-fire-tint-strong bg-fire-tint text-fire-deep-orange"
                  : "border-border bg-surface text-text-muted hover:text-text",
              )}
            >
              Confidence tinggi
            </button>
            <div className="inline-flex rounded-full border border-border bg-surface p-0.5" role="group" aria-label="Granularitas tren">
              {(Object.keys(GRANULARITY_LABEL) as AnalyticsGranularity[]).map((value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => onGranularityChange(value)}
                  aria-pressed={granularity === value}
                  className={clsx(
                    "rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors duration-150",
                    granularity === value
                      ? "bg-fire-tint text-fire-deep-orange"
                      : "text-text-muted hover:text-text",
                  )}
                >
                  {GRANULARITY_LABEL[value]}
                </button>
              ))}
            </div>
          </div>
        }
      >
        <EChart option={trendOption} height={300} ariaLabel="Grafik garis tren hotspot" />
        <p className="mt-2 text-[11px] text-text-subtle">
          {trend ? `${chartNumber(trend.meta.n)} titik data · ${trend.meta.conf === "high" ? "confidence tinggi" : "semua confidence"}` : ""}
        </p>
      </SectionCard>

      <SectionCard
        title="Perbandingan tahun ke tahun"
        description="Kumulatif hotspot menurut hari dalam tahun; tahun berjalan disorot oranye, tahun lain abu-abu, rata-rata historis putus-putus."
        loading={loading && !yearCompare}
        error={yearError}
        empty={!loading && yearEmpty}
        emptyHint="Belum ada data lintas tahun pada filter ini."
      >
        <EChart option={yearOption} height={300} ariaLabel="Grafik kumulatif hotspot per tahun" />
        <p className="mt-2 text-[11px] text-text-subtle">
          {yearCompare?.current_year
            ? `Tahun berjalan: ${yearCompare.current_year} · ${yearCompare.meta.n_years} tahun tersedia`
            : ""}
        </p>
      </SectionCard>
    </div>
  );
}
