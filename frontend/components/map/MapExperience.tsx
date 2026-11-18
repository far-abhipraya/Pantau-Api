"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Map as LeafletMap } from "leaflet";
import { AlertTriangle, Info, RotateCcw } from "lucide-react";

import FilterCard, { type Filters, type LayerKey } from "@/components/map/FilterCard";
import KpiCards from "@/components/map/KpiCards";
import Legend from "@/components/map/Legend";
import MapControls from "@/components/map/MapControls";
import ProvinceDrawer from "@/components/map/ProvinceDrawer";
import TopBar from "@/components/TopBar";
import {
  api,
  type GeoJson,
  type GridFeature,
  type HotspotFeature,
  type Kpi,
  type ProvinceResponse,
  type RiskResponse,
} from "@/lib/api";
import { formatDateTimeWib } from "@/lib/format";

const MapCanvas = dynamic(() => import("@/components/map/MapCanvas"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-bg">
      <div className="flex flex-col items-center gap-2 text-text-muted">
        <div className="size-6 animate-spin rounded-full border-2 border-border border-t-fire-deep-orange" />
        <p className="text-xs">Memuat peta…</p>
      </div>
    </div>
  ),
});

type Viewport = { bbox: string; zoom: number; center: [number, number] };

const DEFAULT_VIEWPORT: Viewport = {
  bbox: "94.5,-11.5,141.5,6.5",
  zoom: 5,
  center: [-2.5, 118],
};

const DEFAULT_LAYERS: Record<LayerKey, boolean> = {
  hotspots: true,
  grid: true,
  risk: false,
  provinces: true,
};

const DEFAULT_FILTERS: Filters = { hours: 24, sensor: "all", minConf: "all" };

const EMPTY_RISK: RiskResponse = {
  type: "FeatureCollection",
  features: [],
  meta: { available: false },
};

const DEFAULT_GEO: GeoJson | null = null;

export default function MapExperience() {
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [layers, setLayers] = useState<Record<LayerKey, boolean>>(DEFAULT_LAYERS);
  const [basemap, setBasemap] = useState<"light" | "satellite">("light");
  const [viewport, setViewport] = useState<Viewport>(DEFAULT_VIEWPORT);
  const [filterCollapsed, setFilterCollapsed] = useState(false);
  const [mobileFilterOpen, setMobileFilterOpen] = useState(false);

  const [points, setPoints] = useState<HotspotFeature[]>([]);
  const [grid, setGrid] = useState<GridFeature[]>([]);
  const [gridResolution, setGridResolution] = useState<number | null>(null);
  const [pointsTruncated, setPointsTruncated] = useState(false);
  const [loadingTiles, setLoadingTiles] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);

  const [kpi, setKpi] = useState<Kpi | null>(null);
  const [kpiRetrying, setKpiRetrying] = useState(false);
  const [kpiError, setKpiError] = useState<string | null>(null);

  const [provinceData, setProvinceData] = useState<ProvinceResponse | null>(null);
  const [geo, setGeo] = useState<GeoJson | null>(DEFAULT_GEO);
  const [risk, setRisk] = useState<RiskResponse>(EMPTY_RISK);
  const [selectedProvince, setSelectedProvince] = useState<string | null>(null);

  const mapRef = useRef<LeafletMap | null>(null);
  const [retryToken, setRetryToken] = useState(0);

  const riskAvailable = risk.meta.available;

  useEffect(() => {
    const controller = new AbortController();
    api
      .kpi(filters.hours, { signal: controller.signal })
      .then((data) => {
        setKpi(data);
        setKpiError(null);
      })
      .catch((error: unknown) => {
        if ((error as Error).name !== "AbortError") setKpiError((error as Error).message);
      })
      .finally(() => setKpiRetrying(false));
    return () => controller.abort();
  }, [filters.hours, retryToken]);

  const kpiLoading =
    !kpiError && (kpi === null || kpi.window_hours !== filters.hours || kpiRetrying);

  useEffect(() => {
    const controller = new AbortController();
    api
      .provinces(24, { signal: controller.signal })
      .then((data) => setProvinceData(data))
      .catch(() => undefined);
    api
      .provincesGeo({ signal: controller.signal })
      .then((data) => setGeo(data))
      .catch(() => undefined);
    api
      .risk({ signal: controller.signal })
      .then((data) => setRisk(data))
      .catch(() => undefined);
    return () => controller.abort();
  }, [retryToken]);

  const useGrid = layers.grid && viewport.zoom < 7;

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setMapError(null);
      if (useGrid) {
        setLoadingTiles(true);
        api
          .grid(viewport.bbox, { zoom: viewport.zoom, hours: filters.hours }, { signal: controller.signal })
          .then((data) => {
            setGrid(data.features);
            setGridResolution(data.meta.resolution);
          })
          .catch((error: unknown) => {
            if ((error as Error).name !== "AbortError") setMapError((error as Error).message);
          })
          .finally(() => setLoadingTiles(false));
      } else if (layers.hotspots) {
        setLoadingTiles(true);
        api
          .hotspots(
            viewport.bbox,
            {
              hours: filters.hours,
              sensor: filters.sensor,
              min_conf: filters.minConf,
              limit: 20000,
            },
            { signal: controller.signal },
          )
          .then((data) => {
            setPoints(data.features);
            setPointsTruncated(data.meta.truncated);
          })
          .catch((error: unknown) => {
            if ((error as Error).name !== "AbortError") setMapError((error as Error).message);
          })
          .finally(() => setLoadingTiles(false));
      }
    }, 280);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [viewport.bbox, viewport.zoom, filters, layers.hotspots, useGrid, retryToken]);

  const onViewportChange = useCallback((next: Viewport) => {
    setViewport(next);
  }, []);

  const onMapReady = useCallback((map: LeafletMap) => {
    mapRef.current = map;
  }, []);

  const summary = useMemo(() => {
    if (!selectedProvince || !provinceData) return null;
    return provinceData.provinces.find((item) => item.province === selectedProvince) ?? null;
  }, [provinceData, selectedProvince]);

  const activeCount = (layers.grid && useGrid ? grid.length : 0) + (layers.hotspots && !useGrid ? points.length : 0);
  const showEmpty = !loadingTiles && !mapError && activeCount === 0;
  const stale = kpi?.freshness.status === "stale";

  const resetView = () => {
    mapRef.current?.flyTo(DEFAULT_VIEWPORT.center, DEFAULT_VIEWPORT.zoom, { duration: 0.4 });
    setFilters(DEFAULT_FILTERS);
    setLayers(DEFAULT_LAYERS);
  };

  return (
    <main className="relative h-dvh w-full overflow-hidden bg-bg">
      <div className="absolute inset-0">
        <MapCanvas
          points={points}
          grid={grid}
          gridResolution={gridResolution}
          showPoints={layers.hotspots && !useGrid}
          showGrid={useGrid}
          showProvinces={layers.provinces}
          showRisk={layers.risk}
          provinces={geo}
          risk={risk}
          basemap={basemap}
          onViewportChange={onViewportChange}
          onProvinceSelect={(province) => setSelectedProvince(province)}
          onMapReady={onMapReady}
        />
      </div>

      <TopBar updatedAt={kpi?.freshness.max_acq_ts ?? null} freshness={kpi?.freshness.status} fadeOnIdle />

      <FilterCard
        filters={filters}
        onChange={setFilters}
        layers={layers}
        onToggleLayer={(key) =>
          setLayers((current) => ({ ...current, [key]: !current[key] }))
        }
        riskAvailable={riskAvailable}
        collapsed={filterCollapsed}
        onToggleCollapsed={() => setFilterCollapsed((value) => !value)}
        mobileOpen={mobileFilterOpen}
        onOpenMobile={() => setMobileFilterOpen(true)}
        onCloseMobile={() => setMobileFilterOpen(false)}
      />

      <KpiCards kpi={kpi} loading={kpiLoading} error={kpiError} />

      <Legend showRisk={layers.risk && riskAvailable} gridResolution={gridResolution} />

      <MapControls
        onZoomIn={() => mapRef.current?.zoomIn()}
        onZoomOut={() => mapRef.current?.zoomOut()}
        onReset={resetView}
        basemap={basemap}
        onChangeBasemap={setBasemap}
      />

      <ProvinceDrawer
        province={selectedProvince}
        summary={summary}
        loading={false}
        onClose={() => setSelectedProvince(null)}
      />

      {loadingTiles ? (
        <div className="pointer-events-none absolute inset-x-0 top-32 z-[997] flex justify-center">
          <p className="flex items-center gap-2 rounded-full bg-surface/95 px-3 py-1 text-[11px] font-medium text-text-muted shadow-[var(--shadow-card)]">
            <span className="size-3 animate-spin rounded-full border-2 border-border border-t-fire-deep-orange" />
            Memuat data peta…
          </p>
        </div>
      ) : null}

      {stale ? (
        <div className="pointer-events-none absolute inset-x-0 top-20 z-[998] flex justify-center">
          <p className="pointer-events-auto flex items-center gap-2 rounded-full border border-warning/40 bg-[#FFF7E6] px-3 py-1.5 text-xs font-medium text-[#8A4B00] shadow-[var(--shadow-card)]">
            <AlertTriangle className="size-3.5" aria-hidden />
            Data tertunda sejak {formatDateTimeWib(kpi?.freshness.max_acq_ts ?? null)}
          </p>
        </div>
      ) : null}

      {layers.hotspots && !useGrid && pointsTruncated ? (
        <div className="pointer-events-none absolute inset-x-0 top-32 z-[997] flex justify-center md:top-36">
          <p className="pointer-events-auto flex items-center gap-2 rounded-full bg-surface/95 px-3 py-1.5 text-[11px] text-text-muted shadow-[var(--shadow-card)]">
            <Info className="size-3.5 text-info" aria-hidden />
            Menampilkan 20.000 titik pertama. Perbesar peta untuk detail.
          </p>
        </div>
      ) : null}

      {showEmpty ? (
        <div className="pointer-events-none absolute inset-0 z-[996] flex items-center justify-center px-4">
          <div className="pointer-events-auto card max-w-xs p-5 text-center">
            <p className="font-display text-base font-semibold">Tidak ada hotspot pada filter ini</p>
            <p className="mt-1 text-xs text-text-muted">
              Coba perlebar jendela waktu, matikan filter confidence, atau geser peta.
            </p>
            <button
              type="button"
              onClick={resetView}
              className="mt-3 inline-flex h-9 items-center gap-1.5 rounded-lg bg-fire-deep-orange px-3 text-xs font-semibold text-white"
            >
              <RotateCcw className="size-3.5" aria-hidden /> Reset filter
            </button>
          </div>
        </div>
      ) : null}

      {mapError ? (
        <div className="pointer-events-none absolute inset-x-0 bottom-6 z-[996] flex justify-center px-4">
          <div className="pointer-events-auto flex items-center gap-2 rounded-lg border border-danger/30 bg-surface px-3 py-2 text-xs text-text shadow-[var(--shadow-floating)]">
            <AlertTriangle className="size-4 text-danger" aria-hidden />
            <span>Gagal memuat data peta: {mapError}</span>
            <button
              type="button"
              onClick={() => {
                setKpiError(null);
                setKpiRetrying(true);
                setRetryToken((value) => value + 1);
              }}
              className="rounded-md bg-surface-muted px-2 py-1 font-semibold text-text hover:bg-border"
            >
              Coba lagi
            </button>
          </div>
        </div>
      ) : null}

      <p className="pointer-events-none absolute bottom-2 left-1/2 z-[995] hidden -translate-x-1/2 rounded-full bg-surface/80 px-3 py-1 text-[10px] text-text-subtle md:block">
        {useGrid ? `Mode agregasi grid ${gridResolution ?? ""}°` : "Mode titik hotspot"} · maksimum 20.000 titik per permintaan
      </p>
    </main>
  );
}
