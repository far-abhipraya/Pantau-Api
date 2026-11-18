"use client";

import clsx from "clsx";

export type TabItem<T extends string> = { value: T; label: string; badge?: number };

export default function Tabs<T extends string>({
  items,
  value,
  onChange,
  ariaLabel,
}: {
  items: TabItem<T>[];
  value: T;
  onChange: (value: T) => void;
  ariaLabel: string;
}) {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className="inline-flex gap-1 rounded-xl border border-border bg-surface-muted p-1"
    >
      {items.map((item) => {
        const active = item.value === value;
        return (
          <button
            key={item.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(item.value)}
            className={clsx(
              "flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-sm font-medium transition-colors duration-150",
              active
                ? "bg-surface text-fire-deep-orange shadow-[var(--shadow-card)]"
                : "text-text-muted hover:text-text",
            )}
          >
            {item.label}
            {item.badge ? (
              <span className="rounded-full bg-danger/10 px-1.5 text-[10px] font-semibold text-danger">
                {item.badge}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
