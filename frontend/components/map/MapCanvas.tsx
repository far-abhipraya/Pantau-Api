"use client";

import { useEffect, useMemo } from "react";
import L from "leaflet";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import Supercluster from "supercluster";

import "leaflet/dist/leaflet.css";

import type { GeoJson, GridFeature, HotspotFeature, HotspotProperties, RiskResponse } from "@/lib/api";
import { CONFIDENCE_COLOR, confidenceLabel, formatDateTimeWib, formatNumber, frpRadius } from "@/lib/format";

export type Viewport = { bbox: string; zoom: number; center: [number, number] };

export type MapProps = {
  points: HotspotFeature[];
  grid: GridFeature[];
  gridResolution: number | null;
  showPoints: boolean;
  showGrid: boolean;
  showProvinces: boolean;
  showRisk: boolean;
  provinces: GeoJson | null;
  risk: RiskResponse | null;
  basemap: "light" | "satellite";
  onViewportChange: (viewport: Viewport) => void;
  onProvinceSelect: (province: string) => void;
  onMapReady: (map: L.Map) => void;
};

const BASEMAPS = {
  light: {
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors · Hotspot: NASA FIRMS',
    maxZoom: 19,
  },
  satellite: {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: "Esri, Maxar, Earthstar Geographics · Hotspot: NASA FIRMS",
    maxZoom: 18,
  },
} as const;

function escapeHtml(value: unknown): string {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function pointPopup(properties: HotspotProperties, coordinates: [number, number]): string {
  const province = properties.province === "UNKNOWN" ? "Luar wilayah" : properties.province;
  const color = CONFIDENCE_COLOR[properties.confidence_level] ?? "#F76707";
  return `
    <div style="min-width:180px">
      <p style="margin:0 0 4px;font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:#D9B8AC">Hotspot</p>
      <p style="margin:0 0 6px;font-size:13px;font-weight:600;color:#FBEFE9">${escapeHtml(formatDateTimeWib(properties.acq_ts_wib))}</p>
      <dl style="display:grid;grid-template-columns:auto 1fr;gap:2px 10px;margin:0">
        <dt style="color:#D9B8AC">Koordinat</dt><dd style="margin:0">${coordinates[1].toFixed(3)}, ${coordinates[0].toFixed(3)}</dd>
        <dt style="color:#D9B8AC">Sensor</dt><dd style="margin:0">${escapeHtml(properties.instrument)} · ${escapeHtml(properties.satellite)}</dd>
        <dt style="color:#D9B8AC">Confidence</dt>
        <dd style="margin:0"><span style="display:inline-flex;align-items:center;gap:4px"><span style="width:7px;height:7px;border-radius:99px;background:${color}"></span>${escapeHtml(confidenceLabel(properties.confidence_level))} (${formatNumber(properties.confidence_score)})</span></dd>
        <dt style="color:#D9B8AC">FRP</dt><dd style="margin:0">${formatNumber(Number(properties.frp))} MW</dd>
        <dt style="color:#D9B8AC">Provinsi</dt><dd style="margin:0">${escapeHtml(province)}</dd>
      </dl>
    </div>`;
}

function ViewportBridge({ onChange }: { onChange: (viewport: Viewport) => void }) {
  const map = useMap();

  useEffect(() => {
    const emit = () => {
      const center = map.getCenter();
      onChange({
        bbox: [map.getBounds().getWest(), map.getBounds().getSouth(), map.getBounds().getEast(), map.getBounds().getNorth()]
          .map((value) => Number(value.toFixed(4)))
          .join(","),
        zoom: Math.round(map.getZoom()),
        center: [center.lat, center.lng],
      });
    };
    emit();
    map.on("moveend zoomend", emit);
    return () => {
      map.off("moveend zoomend", emit);
    };
  }, [map, onChange]);

  return null;
}

function GridLayer({ features }: { features: GridFeature[] }) {
  const map = useMap();

  useEffect(() => {
    if (!features.length) return;
    const layer = L.geoJSON(features as unknown as GeoJSON.GeoJsonObject, {
      style: (feature) => {
        const count = Number((feature?.properties as { hotspot_count?: number })?.hotspot_count ?? 0);
        const level = count > 10 ? 3 : count > 5 ? 2 : count > 2 ? 1 : 0;
        const colors = ["#FCC419", "#FD7E14", "#E03131", "#7A0C1E"];
        return {
          color: "#FFFFFF",
          weight: 0.6,
          opacity: 0.7,
          fillColor: colors[level],
          fillOpacity: 0.55 + level * 0.08,
        };
      },
      onEachFeature: (feature, featureLayer) => {
        const props = feature.properties as {
          hotspot_count: number;
          high_count: number;
          province: string | null;
          frp_max: number;
        };
        const province = props.province === "UNKNOWN" || !props.province ? "Luar wilayah" : props.province;
        featureLayer.bindPopup(
          `<div style="min-width:140px">
             <p style="margin:0;font-size:11px;color:#D9B8AC">Sel grid</p>
             <p style="margin:2px 0 6px;font-size:18px;font-weight:700">${formatNumber(props.hotspot_count)} hotspot</p>
             <p style="margin:0;color:#D9B8AC">Confidence tinggi: ${formatNumber(props.high_count)}</p>
             <p style="margin:0;color:#D9B8AC">FRP maks: ${formatNumber(props.frp_max)} MW</p>
             <p style="margin:4px 0 0">${escapeHtml(province)}</p>
           </div>`,
          { closeButton: true },
        );
      },
    });
    layer.addTo(map);
    return () => {
      layer.remove();
    };
  }, [features, map]);

  return null;
}

type ClusterProps = HotspotProperties & {
  cluster?: boolean;
  point_count?: number;
  cluster_id?: number;
};

function PointsLayer({ points }: { points: HotspotFeature[] }) {
  const map = useMap();

  const index = useMemo(() => {
    if (points.length < 800) return null;
    return new Supercluster<ClusterProps>({ radius: 48, maxZoom: 11, minPoints: 3 }).load(
      points.map((point) => ({
        type: "Feature" as const,
        geometry: point.geometry,
        properties: point.properties as ClusterProps,
      })),
    );
  }, [points]);

  useEffect(() => {
    if (!points.length) return;
    const renderer = L.canvas({ padding: 0.4 });
    const group = L.layerGroup().addTo(map);

    const drawPoint = (properties: HotspotProperties, coordinates: [number, number]) => {
      const color = CONFIDENCE_COLOR[properties.confidence_level] ?? "#F76707";
      const marker = L.circleMarker([coordinates[1], coordinates[0]], {
        radius: frpRadius(Number(properties.frp)),
        color: "#FFFFFF",
        weight: 1,
        fillColor: color,
        fillOpacity: 0.9,
        renderer,
      });
      marker.bindPopup(pointPopup(properties, coordinates));
      group.addLayer(marker);
    };

    const render = () => {
      group.clearLayers();
      const bounds = map.getBounds();
      const zoom = Math.round(map.getZoom());
      if (!index) {
        for (const point of points) {
          drawPoint(point.properties, point.geometry.coordinates);
        }
        return;
      }
      const clusters = index.getClusters(
        [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()],
        zoom,
      );
      for (const cluster of clusters) {
        const props = cluster.properties;
        const [lon, lat] = cluster.geometry.coordinates;
        if (props.cluster) {
          const count = props.point_count ?? 0;
          const size = count > 999 ? 46 : count > 99 ? 40 : 34;
          const marker = L.marker([lat, lon], {
            icon: L.divIcon({
              className: "",
              html: `<div style="display:flex;align-items:center;justify-content:center;width:${size}px;height:${size}px;border-radius:999px;background:#D9480F;color:#fff;font-size:12px;font-weight:700;border:2px solid #fff;box-shadow:0 2px 6px rgba(31,26,23,.25)">${formatNumber(count)}</div>`,
              iconSize: [size, size],
              iconAnchor: [size / 2, size / 2],
            }),
          });
          marker.on("click", () => {
            map.setView([lat, lon], Math.min(index.getClusterExpansionZoom(props.cluster_id ?? 0), 16));
          });
          group.addLayer(marker);
        } else {
          drawPoint(props, [lon, lat]);
        }
      }
    };

    render();
    map.on("moveend zoomend", render);
    return () => {
      map.off("moveend zoomend", render);
      group.remove();
    };
  }, [points, index, map]);

  return null;
}

function ProvinceLayer({
  data,
  onSelect,
}: {
  data: GeoJson | null;
  onSelect: (province: string) => void;
}) {
  const map = useMap();

  useEffect(() => {
    if (!data) return;
    const layer = L.geoJSON(data as unknown as GeoJSON.GeoJsonObject, {
      style: {
        color: "#B8A99C",
        weight: 1,
        opacity: 0.7,
        fillColor: "#F76707",
        fillOpacity: 0,
      },
      onEachFeature: (feature, featureLayer) => {
        const name = String((feature.properties as { name?: string })?.name ?? "");
        featureLayer.on({
          mouseover: (event) => {
            const target = event.target as L.Path;
            target.setStyle({ weight: 2, fillOpacity: 0.06 });
            target.bringToFront();
          },
          mouseout: (event) => {
            const target = event.target as L.Path;
            target.setStyle({ weight: 1, fillOpacity: 0 });
          },
          click: () => onSelect(name),
        });
        featureLayer.bindTooltip(name, { sticky: true, direction: "top", className: "text-xs" });
      },
    });
    layer.addTo(map);
    return () => {
      layer.remove();
    };
  }, [data, map, onSelect]);

  return null;
}

function RiskLayer({ risk, visible }: { risk: RiskResponse | null; visible: boolean }) {
  const map = useMap();

  useEffect(() => {
    if (!visible || !risk?.meta.available) return;
    const colors: Record<string, string> = {
      rendah: "#FCC419",
      sedang: "#FD7E14",
      tinggi: "#E03131",
      "sangat tinggi": "#7A0C1E",
    };
    const layer = L.geoJSON(risk as unknown as GeoJSON.GeoJsonObject, {
      pointToLayer: (feature, latlng) => {
        const category = String(
          (feature.properties as { risk_category?: string })?.risk_category ?? "rendah",
        ).toLowerCase();
        return L.circleMarker(latlng, {
          radius: 7,
          color: "#FFFFFF",
          weight: 1,
          fillColor: colors[category] ?? "#FCC419",
          fillOpacity: 0.8,
        });
      },
    });
    layer.addTo(map);
    return () => {
      layer.remove();
    };
  }, [risk, visible, map]);

  return null;
}

function ReadyBridge({ onReady }: { onReady: (map: L.Map) => void }) {
  const map = useMap();
  useEffect(() => {
    onReady(map);
  }, [map, onReady]);
  return null;
}

function MapCleanup() {
  const map = useMap();
  useEffect(
    () => () => {
      map.remove();
    },
    [map],
  );
  return null;
}

function MapRuntime() {
  return null;
}

export default function MapCanvas({
  points,
  grid,
  showPoints,
  showGrid,
  showProvinces,
  showRisk,
  provinces,
  risk,
  basemap,
  onViewportChange,
  onProvinceSelect,
  onMapReady,
}: MapProps) {
  const tiles = BASEMAPS[basemap];

  return (
    <MapContainer
      key={basemap}
      center={[-2.5, 118]}
      zoom={5}
      minZoom={3}
      maxZoom={18}
      zoomControl={false}
      scrollWheelZoom
      worldCopyJump
      className="h-full w-full"
      attributionControl
    >
      <TileLayer
        key={basemap}
        url={tiles.url}
        attribution={tiles.attribution}
        maxZoom={tiles.maxZoom}
      />
      <ViewportBridge onChange={onViewportChange} />
      <ReadyBridge onReady={onMapReady} />
      <MapCleanup />
      {showGrid && grid.length > 0 ? <GridLayer features={grid} /> : null}
      {showPoints && points.length > 0 ? <PointsLayer points={points} /> : null}
      {showProvinces ? <ProvinceLayer data={provinces} onSelect={onProvinceSelect} /> : null}
      <RiskLayer risk={risk} visible={showRisk} />
      <MapRuntime />
    </MapContainer>
  );
}
