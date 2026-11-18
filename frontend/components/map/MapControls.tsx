"use client";

import { Layers, LocateFixed, Minus, Plus } from "lucide-react";
import clsx from "clsx";

type Props = {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
  basemap: "light" | "satellite";
  onChangeBasemap: (basemap: "light" | "satellite") => void;
};

export default function MapControls({
  onZoomIn,
  onZoomOut,
  onReset,
  basemap,
  onChangeBasemap,
}: Props) {
  return (
    <div className="absolute bottom-20 right-3 z-[1000] flex flex-col items-end gap-2 md:bottom-6">
      <div className="flex overflow-hidden rounded-lg border border-border bg-surface shadow-[var(--shadow-card)]">
        <button
          type="button"
          onClick={() => onChangeBasemap("light")}
          aria-pressed={basemap === "light"}
          className={clsx(
            "px-2.5 py-1.5 text-[11px] font-medium transition-colors",
            basemap === "light" ? "bg-fire-tint text-fire-deep-orange" : "text-text-muted hover:bg-surface-muted",
          )}
        >
          Terang
        </button>
        <button
          type="button"
          onClick={() => onChangeBasemap("satellite")}
          aria-pressed={basemap === "satellite"}
          className={clsx(
            "flex items-center gap-1 border-l border-border px-2.5 py-1.5 text-[11px] font-medium transition-colors",
            basemap === "satellite" ? "bg-fire-tint text-fire-deep-orange" : "text-text-muted hover:bg-surface-muted",
          )}
        >
          <Layers className="size-3" aria-hidden /> Satelit
        </button>
      </div>

      <div className="flex flex-col overflow-hidden rounded-lg border border-border bg-surface shadow-[var(--shadow-card)]">
        <button
          type="button"
          onClick={onZoomIn}
          aria-label="Perbesar peta"
          className="flex size-9 items-center justify-center text-text-muted transition-colors hover:bg-surface-muted hover:text-text"
        >
          <Plus className="size-4" aria-hidden />
        </button>
        <button
          type="button"
          onClick={onZoomOut}
          aria-label="Perkecil peta"
          className="flex size-9 items-center justify-center border-t border-border text-text-muted transition-colors hover:bg-surface-muted hover:text-text"
        >
          <Minus className="size-4" aria-hidden />
        </button>
      </div>

      <button
        type="button"
        onClick={onReset}
        className="flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-2 text-[11px] font-medium text-text shadow-[var(--shadow-card)] transition-colors hover:bg-surface-muted"
      >
        <LocateFixed className="size-3.5 text-fire-deep-orange" aria-hidden />
        Reset tampilan
      </button>
    </div>
  );
}
