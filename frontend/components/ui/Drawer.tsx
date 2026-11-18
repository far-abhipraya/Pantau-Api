"use client";

import { useEffect } from "react";
import { X } from "lucide-react";

export default function Drawer({
  open,
  title,
  subtitle,
  onClose,
  children,
  width = "w-full sm:w-[520px]",
}: {
  open: boolean;
  title: string;
  subtitle?: React.ReactNode;
  onClose: () => void;
  children: React.ReactNode;
  width?: string;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[1300] flex justify-end">
      <button
        type="button"
        aria-label="Tutup panel"
        className="absolute inset-0 bg-ember/40"
        onClick={onClose}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`relative flex h-full ${width} flex-col border-l border-border bg-surface shadow-[var(--shadow-floating)]`}
      >
        <header className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
          <div>
            <h2 className="font-display text-lg font-bold leading-6">{title}</h2>
            {subtitle ? <div className="mt-1 text-xs text-text-muted">{subtitle}</div> : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Tutup"
            className="rounded-md p-1 text-text-muted transition-colors hover:bg-surface-muted"
          >
            <X className="size-5" aria-hidden />
          </button>
        </header>
        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
      </aside>
    </div>
  );
}
