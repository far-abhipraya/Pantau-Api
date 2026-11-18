"use client";

import { ChevronLeft, Layers, SlidersHorizontal, X } from "lucide-react";
import clsx from "clsx";

import type { ConfidenceFilter, SensorFilter, WindowHours } from "@/lib/api";

export type LayerKey = "hotspots" | "grid" | "risk" | "provinces";

export type Filters = {
  hours: WindowHours;
  sensor: SensorFilter;
  minConf: ConfidenceFilter;
};

type Props = {
  filters: Filters;
  onChange: (filters: Filters) => void;
  layers: Record<LayerKey, boolean>;
  onToggleLayer: (key: LayerKey) => void;
  riskAvailable: boolean;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  mobileOpen: boolean;
  onOpenMobile: () => void;
  onCloseMobile: () => void;
};

const WINDOW_OPTIONS: { value: WindowHours; label: string }[] = [
  { value: 24, label: "24 jam" },
  { value: 48, label: "48 jam" },
  { value: 168, label: "7 hari" },
];

const SENSOR_OPTIONS: { value: SensorFilter; label: string }[] = [
  { value: "all", label: "Semua" },
  { value: "viirs", label: "VIIRS" },
  { value: "modis", label: "MODIS" },
];

const CONFIDENCE_OPTIONS: { value: ConfidenceFilter; label: string }[] = [
  { value: "all", label: "Semua" },
  { value: "nominal", label: "Nominal+" },
  { value: "high", label: "High" },
];

const LAYERS: { key: LayerKey; label: string; note?: string }[] = [
  { key: "hotspots", label: "Hotspot" },
  { key: "grid", label: "Densitas grid" },
  { key: "risk", label: "Prediksi risiko 7 hari", note: "Fase 6" },
  { key: "provinces", label: "Batas provinsi" },
];

function Segmented<T extends string | number>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="space-y-1.5">
      <p className="field-label">{label}</p>
      <div className="flex rounded-lg border border-border bg-surface-muted p-0.5" role="group" aria-label={label}>
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            aria-pressed={value === option.value}
            onClick={() => onChange(option.value)}
            className={clsx(
              "flex-1 rounded-md px-2 py-1.5 text-xs font-medium transition-colors duration-150",
              value === option.value
                ? "bg-surface text-fire-deep-orange shadow-[var(--shadow-card)]"
                : "text-text-muted hover:text-text",
            )}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function Toggle({
  checked,
  onChange,
  label,
  note,
  disabled,
}: {
  checked: boolean;
  onChange: () => void;
  label: string;
  note?: string;
  disabled?: boolean;
}) {
  return (
    <label className={clsx("flex items-center justify-between gap-2 py-1", disabled && "opacity-60")}>
      <span className="flex items-center gap-1.5 text-sm text-text">
        {label}
        {note ? (
          <span className="rounded-full border border-border px-1.5 py-0.5 text-[10px] text-text-subtle">
            {note}
          </span>
        ) : null}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={onChange}
        className={clsx(
          "relative h-5 w-9 shrink-0 rounded-full transition-colors duration-150",
          checked ? "bg-fire-deep-orange" : "bg-border",
          disabled && "cursor-not-allowed",
        )}
      >
        <span
          className={clsx(
            "absolute top-0.5 size-4 rounded-full bg-white shadow-sm transition-all duration-150",
            checked ? "left-4.5" : "left-0.5",
          )}
        />
      </button>
    </label>
  );
}

function FilterContent({
  filters,
  onChange,
  layers,
  onToggleLayer,
  riskAvailable,
}: Pick<Props, "filters" | "onChange" | "layers" | "onToggleLayer" | "riskAvailable">) {
  return (
    <div className="space-y-4">
      <Segmented
        label="Jendela waktu"
        value={filters.hours}
        options={WINDOW_OPTIONS}
        onChange={(hours) => onChange({ ...filters, hours })}
      />
      <Segmented
        label="Sensor"
        value={filters.sensor}
        options={SENSOR_OPTIONS}
        onChange={(sensor) => onChange({ ...filters, sensor })}
      />
      <Segmented
        label="Confidence minimum"
        value={filters.minConf}
        options={CONFIDENCE_OPTIONS}
        onChange={(minConf) => onChange({ ...filters, minConf })}
      />
      <div className="border-t border-border pt-2">
        <p className="field-label mb-1 flex items-center gap-1.5">
          <Layers className="size-3" aria-hidden /> Lapisan
        </p>
        {LAYERS.map((layer) => (
          <Toggle
            key={layer.key}
            label={layer.label}
            note={layer.note}
            checked={layers[layer.key]}
            disabled={layer.key === "risk" && !riskAvailable}
            onChange={() => onToggleLayer(layer.key)}
          />
        ))}
      </div>
      <p className="rounded-lg bg-surface-muted px-2.5 py-2 text-[11px] leading-relaxed text-text-muted">
        Hotspot adalah indikasi anomali suhu satelit, bukan kepastian kebakaran.
      </p>
    </div>
  );
}

export default function FilterCard(props: Props) {
  const {
    collapsed,
    onToggleCollapsed,
    mobileOpen,
    onOpenMobile,
    onCloseMobile,
    filters,
    onChange,
    layers,
    onToggleLayer,
    riskAvailable,
  } = props;

  return (
    <>
      {/* Desktop: kartu melayang yang bisa diciutkan. */}
      <div className="pointer-events-none absolute left-3 top-20 z-[1000] hidden md:block">
        <div className="pointer-events-auto">
          {collapsed ? (
            <button
              type="button"
              onClick={onToggleCollapsed}
              className="flex h-11 items-center gap-2 rounded-xl border border-border bg-surface px-3 text-xs font-semibold text-text shadow-[var(--shadow-floating)]"
            >
              <SlidersHorizontal className="size-4 text-fire-deep-orange" aria-hidden />
              Filter
            </button>
          ) : (
            <div className="w-72 rounded-2xl border border-border bg-surface p-4 shadow-[var(--shadow-floating)]">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="font-display text-sm font-semibold">Filter &amp; lapisan</h2>
                <button
                  type="button"
                  onClick={onToggleCollapsed}
                  aria-label="Ciutkan filter"
                  className="rounded-md p-1 text-text-muted hover:bg-surface-muted"
                >
                  <ChevronLeft className="size-4" aria-hidden />
                </button>
              </div>
              <FilterContent
                filters={filters}
                onChange={onChange}
                layers={layers}
                onToggleLayer={onToggleLayer}
                riskAvailable={riskAvailable}
              />
            </div>
          )}
        </div>
      </div>

      {/* Tablet/mobile: tombol + bottom sheet. */}
      <button
        type="button"
        onClick={() => (mobileOpen ? onCloseMobile() : onOpenMobile())}
        className="pointer-events-auto absolute bottom-6 left-3 z-[1000] flex h-11 items-center gap-2 rounded-full border border-border bg-surface px-4 text-sm font-semibold shadow-[var(--shadow-floating)] md:hidden"
      >
        <SlidersHorizontal className="size-4 text-fire-deep-orange" aria-hidden />
        Filter
      </button>

      {mobileOpen ? (
        <div className="absolute inset-0 z-[1100] md:hidden">
          <button
            type="button"
            aria-label="Tutup filter"
            className="absolute inset-0 bg-ember/40"
            onClick={onCloseMobile}
          />
          <div className="absolute inset-x-0 bottom-0 max-h-[85dvh] overflow-y-auto rounded-t-2xl border-t border-border bg-surface p-4 pb-6 shadow-[var(--shadow-floating)]">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-display text-base font-semibold">Filter &amp; lapisan</h2>
              <button
                type="button"
                onClick={onCloseMobile}
                aria-label="Tutup"
                className="rounded-md p-1 text-text-muted hover:bg-surface-muted"
              >
                <X className="size-5" aria-hidden />
              </button>
            </div>
            <FilterContent
              filters={filters}
              onChange={onChange}
              layers={layers}
              onToggleLayer={onToggleLayer}
              riskAvailable={riskAvailable}
            />
          </div>
        </div>
      ) : null}
    </>
  );
}
