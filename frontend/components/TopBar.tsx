"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Flame } from "lucide-react";

import { formatTimeWib } from "@/lib/format";

const NAV_ITEMS = [
  { href: "/", label: "Peta" },
  { href: "/data", label: "Data" },
  { href: "/analytics", label: "Analitik" },
];

type Props = {
  updatedAt?: string | null;
  freshness?: "fresh" | "delayed" | "stale" | "unknown";
  fadeOnIdle?: boolean;
};

export default function TopBar({ updatedAt, freshness = "unknown", fadeOnIdle = false }: Props) {
  const pathname = usePathname();
  const [idle, setIdle] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!fadeOnIdle) return;
    const schedule = () => {
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => setIdle(true), 3000);
    };
    const wake = () => {
      setIdle(false);
      schedule();
    };
    schedule();
    window.addEventListener("pointermove", wake);
    window.addEventListener("keydown", wake);
    window.addEventListener("touchstart", wake);
    return () => {
      if (timer.current) clearTimeout(timer.current);
      window.removeEventListener("pointermove", wake);
      window.removeEventListener("keydown", wake);
      window.removeEventListener("touchstart", wake);
    };
  }, [fadeOnIdle]);

  const dotColor =
    freshness === "fresh"
      ? "bg-success"
      : freshness === "delayed"
        ? "bg-warning"
        : freshness === "stale"
          ? "bg-danger"
          : "bg-neutral-series";

  return (
    <header className="pointer-events-none fixed inset-x-0 top-3 z-[1200] flex justify-center px-3">
      <div
        className={`pointer-events-auto flex h-13 w-full max-w-[1120px] items-center gap-3 rounded-full border border-white/60 bg-surface/95 px-3 shadow-[var(--shadow-floating)] backdrop-blur transition-opacity duration-200 sm:h-14 sm:gap-5 sm:px-4 ${
          idle ? "opacity-65" : "opacity-100"
        }`}
      >
        <Link href="/" className="flex items-center gap-2 pl-1">
          <span className="flex size-8 items-center justify-center rounded-full bg-[linear-gradient(135deg,#F76707_0%,#C92A2A_100%)]">
            <Flame className="size-4 text-white" strokeWidth={2.4} aria-hidden />
          </span>
          <span className="font-display text-[17px] font-bold tracking-tight">PantauApi</span>
        </Link>

        <nav className="flex items-center gap-1" aria-label="Navigasi utama">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors duration-150 ${
                  active
                    ? "bg-fire-tint text-fire-deep-orange"
                    : "text-text-muted hover:bg-surface-muted hover:text-text"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-1.5 rounded-full border border-border/70 px-2.5 py-1 text-[11px] text-text-muted sm:px-3 sm:text-xs">
          <span className={`size-1.5 rounded-full ${dotColor}`} aria-hidden />
          <span className="hidden sm:inline">Diperbarui</span>
          <span className="number font-medium text-text">{formatTimeWib(updatedAt)}</span>
        </div>
      </div>
    </header>
  );
}
