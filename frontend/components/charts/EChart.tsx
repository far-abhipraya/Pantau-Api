"use client";

import { useEffect, useRef } from "react";

type ChartInstance = {
  setOption: (option: unknown, notMerge?: boolean) => void;
  resize: () => void;
  dispose: () => void;
};

type MapRegistration = { name: string; geo: unknown };

/**
 * Pembungkus tipis ECharts. Library diimpor dinamis di dalam effect supaya
 * tidak ikut SSR/bundle awal, dan instance di-resize mengikuti kontainer.
 */
export default function EChart({
  option,
  height = 260,
  ariaLabel,
  mapRegistration,
}: {
  option: unknown;
  height?: number;
  ariaLabel?: string;
  mapRegistration?: MapRegistration;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ChartInstance | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    let cancelled = false;

    void import("echarts").then((echarts) => {
      if (cancelled || !containerRef.current) return;
      if (mapRegistration) {
        echarts.registerMap(mapRegistration.name, mapRegistration.geo as never);
      }
      // Pastikan hanya satu instance per kontainer (mis. saat Fast Refresh).
      echarts.getInstanceByDom(containerRef.current)?.dispose();
      containerRef.current.replaceChildren();
      const chart = echarts.init(containerRef.current, undefined, {
        renderer: "canvas",
      }) as unknown as ChartInstance;
      chartRef.current = chart;
      chart.setOption(option);
    });

    const observer = new ResizeObserver(() => chartRef.current?.resize());
    observer.observe(container);

    return () => {
      cancelled = true;
      observer.disconnect();
      chartRef.current?.dispose();
      chartRef.current = null;
      container.replaceChildren();
    };
    // Option awal cukup dipasang sekali; pembaruan ditangani effect di bawah.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option, true);
  }, [option]);

  return (
    <div
      ref={containerRef}
      role="img"
      aria-label={ariaLabel}
      className="w-full"
      style={{ height }}
    />
  );
}
