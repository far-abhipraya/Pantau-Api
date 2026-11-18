"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

type Props = {
  showRisk: boolean;
  gridResolution: number | null;
};

const CONFIDENCE = [
  { color: "#ffc078", label: "Rendah" },
  { color: "#f76707", label: "Nominal" },
  { color: "#b71c1c", label: "Tinggi" },
];

const GRID_STOPS = [
  { color: "#fcc419", label: "1–2" },
  { color: "#fd7e14", label: "3–5" },
  { color: "#e03131", label: "6–10" },
  { color: "#7a0c1e", label: "> 10" },
];

const RISK = [
  { color: "#fcc419", label: "Rendah" },
  { color: "#fd7e14", label: "Sedang" },
  { color: "#e03131", label: "Tinggi" },
  { color: "#7a0c1e", label: "Sangat tinggi" },
];

export default function Legend({ showRisk, gridResolution }: Props) {
  const [open, setOpen] = useState(true);

  return (
    <div className="pointer-events-none absolute bottom-6 left-3 z-[1000] hidden w-56 md:[@media(min-height:840px)]:block">
      <div className="pointer-events-auto rounded-xl border border-border bg-surface/95 p-3 shadow-[var(--shadow-card)] backdrop-blur">
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          className="flex w-full items-center justify-between text-[11px] font-semibold uppercase tracking-[0.08em] text-text-subtle"
        >
          Legenda
          {open ? <ChevronDown className="size-3.5" aria-hidden /> : <ChevronUp className="size-3.5" aria-hidden />}
        </button>

        {open ? (
          <div className="mt-2 space-y-3 text-[11px] text-text-muted">
            <div>
              <p className="mb-1 font-medium text-text">Confidence</p>
              <div className="flex items-center gap-3">
                {CONFIDENCE.map((item) => (
                  <span key={item.label} className="flex items-center gap-1">
                    <span
                      className="size-2.5 rounded-full border border-white ring-1 ring-border"
                      style={{ background: item.color }}
                      aria-hidden
                    />
                    {item.label}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <p className="mb-1 font-medium text-text">Ukuran titik = FRP</p>
              <div className="flex items-end gap-2">
                {[3, 5, 7, 9].map((size) => (
                  <span
                    key={size}
                    className="rounded-full border border-white bg-fire-orange ring-1 ring-border/70"
                    style={{ width: size, height: size }}
                    aria-hidden
                  />
                ))}
                <span>rendah → tinggi</span>
              </div>
            </div>

            <div>
              <p className="mb-1 font-medium text-text">
                Densitas grid{gridResolution ? ` ${gridResolution}°` : ""}
              </p>
              <div className="flex items-center gap-2">
                {GRID_STOPS.map((item) => (
                  <span key={item.label} className="flex flex-col items-center gap-0.5">
                    <span className="size-3 rounded-sm" style={{ background: item.color }} aria-hidden />
                    <span className="text-[10px] text-text-subtle">{item.label}</span>
                  </span>
                ))}
              </div>
              <p className="mt-1 text-[10px] text-text-subtle">Hotspot per sel per jendela waktu</p>
            </div>

            {showRisk ? (
              <div>
                <p className="mb-1 flex items-center gap-1 font-medium text-text">
                  Estimasi risiko 7 hari
                  <span className="rounded-full border border-fire-deep-orange px-1 text-[9px] text-fire-deep-orange">
                    Prediksi
                  </span>
                </p>
                <div className="grid grid-cols-2 gap-1">
                  {RISK.map((item) => (
                    <span key={item.label} className="flex items-center gap-1">
                      <span className="size-2.5 rounded-sm" style={{ background: item.color }} aria-hidden />
                      {item.label}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
