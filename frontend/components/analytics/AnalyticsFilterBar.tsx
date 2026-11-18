"use client";

import clsx from "clsx";
import { CalendarRange, RefreshCw } from "lucide-react";

import type { AnalyticsConf, AnalyticsWindowDays } from "@/lib/api";
import { formatDateTimeWib } from "@/lib/format";

export const SECTION_LINKS = [
  { id: "ringkasan", label: "Ringkasan" },
  { id: "wilayah", label: "Wilayah" },
  { id: "musiman", label: "Musiman" },
  { id: "faktor", label: "Faktor Pengaruh" },
  { id: "cuaca", label: "Cuaca" },
  { id: "prediksi", label: "Prediksi ML" },
  { id: "validasi", label: "Validasi" },
] as const;

const WINDOWS: { value: AnalyticsWindowDays; label: string }[] = [
  { value: 30, label: "30 hari" },
  { value: 90, label: "90 hari" },
  { value: 365, label: "1 tahun" },
  { value: 0, label: "Semua" },
];

function Segment<T extends string | number>({
  options,
  value,
  onChange,
  label,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
  label: string;
}) {
  return (
    <div
      className="inline-flex shrink-0 items-center rounded-full border border-border bg-surface p-0.5"
      role="group"
      aria-label={label}
    >
      {options.map((option) => (
        <button
          key={String(option.value)}
          type="button"
          onClick={() => onChange(option.value)}
          aria-pressed={option.value === value}
          className={clsx(
            "rounded-full px-2.5 py-1 text-xs font-medium transition-colors duration-150",
            option.value === value
              ? "bg-fire-tint text-fire-deep-orange"
              : "text-text-muted hover:text-text",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export default function AnalyticsFilterBar({
  days,
  onDaysChange,
  province,
  provinces,
  onProvinceChange,
  conf,
  onConfChange,
  onRefresh,
  refreshing,
  updatedAt,
  notice,
  activeSection,
}: {
  days: AnalyticsWindowDays;
  onDaysChange: (value: AnalyticsWindowDays) => void;
  province: string;
  provinces: string[];
  onProvinceChange: (value: string) => void;
  conf: AnalyticsConf;
  onConfChange: (value: AnalyticsConf) => void;
  onRefresh: () => void;
  refreshing: boolean;
  updatedAt: string | null;
  notice: { tone: "success" | "warning"; text: string } | null;
  activeSection: string;
}) {
  return (
    <div className="sticky top-[68px] z-[900] space-y-2 rounded-xl border border-border bg-surface/95 p-2 shadow-[var(--shadow-card)] backdrop-blur sm:top-[72px]">
      <div className="flex items-center gap-2 overflow-x-auto pb-0.5">
        <span className="flex shrink-0 items-center gap-1 pl-1 text-[11px] font-medium text-text-subtle">
          <CalendarRange className="size-3.5" aria-hidden />
          Rentang
        </span>
        <Segment options={WINDOWS} value={days} onChange={onDaysChange} label="Rentang waktu" />

        <label className="sr-only" htmlFor="analytics-province">
          Provinsi
        </label>
        <select
          id="analytics-province"
          value={province}
          onChange={(event) => onProvinceChange(event.target.value)}
          className="shrink-0 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-text focus-visible:outline-2"
        >
          <option value="">Nasional</option>
          {provinces.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>

        <Segment
          options={[
            { value: "all" as AnalyticsConf, label: "Semua confidence" },
            { value: "high" as AnalyticsConf, label: "Confidence tinggi" },
          ]}
          value={conf}
          onChange={onConfChange}
          label="Filter confidence"
        />

        <div className="ml-auto flex shrink-0 items-center gap-2 pl-2">
          <span className="hidden text-[11px] text-text-muted md:inline">
            Diperbarui {formatDateTimeWib(updatedAt)}
          </span>
          <button
            type="button"
            onClick={onRefresh}
            disabled={refreshing}
            className="inline-flex items-center gap-1.5 rounded-full border border-fire-tint-strong bg-fire-tint px-3 py-1 text-xs font-semibold text-fire-deep-orange transition-colors duration-150 hover:bg-fire-tint-strong disabled:opacity-60"
          >
            <RefreshCw className={clsx("size-3.5", refreshing && "animate-spin")} aria-hidden />
            Perbarui agregasi
          </button>
        </div>
      </div>

      <nav className="flex items-center gap-1 overflow-x-auto border-t border-border/70 pt-1.5" aria-label="Navigasi seksi analitik">
        {SECTION_LINKS.map((section) => (
          <a
            key={section.id}
            href={`#${section.id}`}
            aria-current={activeSection === section.id ? "true" : undefined}
            className={clsx(
              "shrink-0 rounded-full px-2.5 py-1 text-xs font-medium transition-colors duration-150",
              activeSection === section.id
                ? "bg-surface-muted text-text"
                : "text-text-muted hover:text-text",
            )}
          >
            {section.label}
          </a>
        ))}
      </nav>

      {notice ? (
        <p
          className={clsx(
            "rounded-lg px-3 py-1.5 text-[11px]",
            notice.tone === "success"
              ? "bg-[#EBFBEE] text-[#2B8A3E]"
              : "bg-[#FFF9DB] text-[#8A4B00]",
          )}
        >
          {notice.text}
        </p>
      ) : null}
    </div>
  );
}
