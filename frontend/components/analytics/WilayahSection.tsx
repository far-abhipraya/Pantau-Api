"use client";

import { useMemo } from "react";

import SectionCard from "@/components/analytics/SectionCard";
import EChart from "@/components/charts/EChart";
import type { AnalyticsRanking, AnalyticsTopGrid, GeoJson } from "@/lib/api";
import { CHART_COLORS, FONT_FAMILY, chartCompact, chartNumber, heatColorStops } from "@/lib/chartFormat";

const MAP_NAME = "pantauapi-provinces";

export default function WilayahSection({
  ranking,
  topGrid,
  geo,
  loading,
  rankingError,
  gridError,
  windowLabel,
}: {
  ranking: AnalyticsRanking | null;
  topGrid: AnalyticsTopGrid | null;
  geo: GeoJson | null;
  loading: boolean;
  rankingError?: string | null;
  gridError?: string | null;
  windowLabel: string;
}) {
  const items = useMemo(() => (ranking?.items ?? []).slice(0, 15), [ranking]);
  const shareByName = useMemo(() => {
    const map = new Map<string, number>();
    (ranking?.items ?? []).forEach((item) => map.set(item.province, item.share_percent));
    return map;
  }, [ranking]);

  const rankingOption = useMemo(() => {
    const ordered = [...items].reverse();
    return {
      textStyle: { fontFamily: FONT_FAMILY },
      grid: { left: 8, right: 52, top: 8, bottom: 8, containLabel: true },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        confine: true,
        formatter: (params: unknown) => {
          const list = params as { name: string; value: number; dataIndex: number }[];
          const item = list[0];
          if (!item) return "";
          const share = shareByName.get(item.name);
          return `<strong>${item.name}</strong><br/>Hotspot: ${chartNumber(item.value)}${
            share !== undefined ? `<br/>Pangsa: ${share.toLocaleString("id-ID")}%` : ""
          }`;
        },
      },
      xAxis: {
        type: "value",
        splitLine: { lineStyle: { color: CHART_COLORS.grid } },
        axisLabel: { color: CHART_COLORS.axis, fontSize: 10, formatter: (value: number) => chartCompact(value) },
      },
      yAxis: {
        type: "category",
        inverse: true,
        data: ordered.map((item) => item.province),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: CHART_COLORS.text, fontSize: 11 },
      },
      series: [
        {
          type: "bar",
          data: ordered.map((item) => item.count),
          barMaxWidth: 18,
          itemStyle: {
            borderRadius: [0, 4, 4, 0],
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 1,
              y2: 0,
              colorStops: [
                { offset: 0, color: "#f76707" },
                { offset: 1, color: "#c92a2a" },
              ],
            },
          },
          label: {
            show: true,
            position: "right",
            fontSize: 10,
            color: CHART_COLORS.axis,
            formatter: (params: { dataIndex: number }) => {
              const item = ordered[params.dataIndex];
              return item ? `${item.share_percent.toLocaleString("id-ID")}%` : "";
            },
          },
        },
      ],
    };
  }, [items, shareByName]);

  const mapOption = useMemo(() => {
    const values = (ranking?.items ?? []).map((item) => ({
      name: item.province,
      value: item.count,
    }));
    const max = values.reduce((acc, item) => Math.max(acc, item.value), 0);
    return {
      textStyle: { fontFamily: FONT_FAMILY },
      tooltip: {
        trigger: "item",
        confine: true,
        formatter: (params: { name: string; value?: number }) => {
          const share = shareByName.get(params.name);
          return `<strong>${params.name}</strong><br/>Hotspot: ${chartNumber(
            Number(params.value ?? 0),
          )}${share !== undefined ? `<br/>Pangsa: ${share.toLocaleString("id-ID")}%` : ""}`;
        },
      },
      visualMap: {
        min: 0,
        max: Math.max(1, max),
        left: 4,
        bottom: 4,
        itemHeight: 70,
        itemWidth: 10,
        text: ["Tinggi", "Rendah"],
        textStyle: { fontSize: 9, color: CHART_COLORS.axis },
        inRange: { color: heatColorStops() },
        calculable: false,
      },
      series: [
        {
          type: "map",
          map: MAP_NAME,
          roam: false,
          scaleLimit: { min: 1, max: 4 },
          data: values,
          itemStyle: { borderColor: "#ffffff", borderWidth: 0.6 },
          label: { show: false },
          emphasis: {
            label: { show: true, fontSize: 10, color: CHART_COLORS.text },
            itemStyle: { areaColor: "#ffa94d" },
          },
        },
      ],
    };
  }, [ranking, shareByName]);

  return (
    <div className="space-y-3">
      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
        <SectionCard
          id="wilayah"
          title="Ranking provinsi"
          description={`15 provinsi teratas · ${windowLabel}.`}
          loading={loading && !ranking}
          error={rankingError}
          empty={!loading && (ranking?.items.length ?? 0) === 0}
          emptyHint="Tidak ada hotspot pada periode ini."
        >
          <EChart option={rankingOption} height={400} ariaLabel="Grafik batang ranking provinsi" />
        </SectionCard>

        <SectionCard
          title="Sebaran provinsi"
          description="Choropleth jumlah hotspot per provinsi pada periode terpilih."
          loading={loading && !ranking}
          error={rankingError}
          empty={!loading && !geo}
          emptyHint="GeoJSON provinsi tidak tersedia."
        >
          {geo ? (
            <EChart
              option={mapOption}
              height={400}
              ariaLabel="Peta choropleth hotspot per provinsi"
              mapRegistration={{ name: MAP_NAME, geo }}
            />
          ) : (
            <div className="h-[400px] animate-pulse rounded bg-surface-muted" />
          )}
        </SectionCard>
      </div>

      <SectionCard
        title="Grid hotspot tertinggi"
        description={`10 sel grid 0,25° dengan hotspot terbanyak · ${windowLabel}.`}
        loading={loading && !topGrid}
        error={gridError}
        empty={!loading && (topGrid?.items.length ?? 0) === 0}
        emptyHint="Tidak ada grid pada periode ini."
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-xs">
            <thead>
              <tr className="border-b border-border text-[11px] uppercase tracking-wide text-text-subtle">
                <th className="py-2 pr-3 font-semibold">#</th>
                <th className="py-2 pr-3 font-semibold">Koordinat pusat grid</th>
                <th className="py-2 pr-3 font-semibold">Provinsi</th>
                <th className="py-2 pr-3 text-right font-semibold">Hotspot</th>
                <th className="py-2 text-right font-semibold">Confidence tinggi</th>
              </tr>
            </thead>
            <tbody>
              {(topGrid?.items ?? []).map((item, index) => (
                <tr key={`${item.grid_lat}-${item.grid_lon}`} className="border-b border-border/60 last:border-0">
                  <td className="number py-2 pr-3 text-text-subtle">{index + 1}</td>
                  <td className="number py-2 pr-3 font-mono text-[11px]">
                    {item.grid_lat.toFixed(2)}, {item.grid_lon.toFixed(2)}
                  </td>
                  <td className="py-2 pr-3">{item.province ?? "—"}</td>
                  <td className="number py-2 pr-3 text-right font-semibold">{chartNumber(item.count)}</td>
                  <td className="number py-2 text-right text-text-muted">{chartNumber(item.high_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-[11px] text-text-subtle">
          Grid adalah sel 0,25° tempat hotspot diagregasi; koordinat menandai pusat sel.
        </p>
      </SectionCard>
    </div>
  );
}
