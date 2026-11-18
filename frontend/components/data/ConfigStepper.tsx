"use client";

import { useState } from "react";
import clsx from "clsx";
import { ChevronDown, ChevronUp, Lock } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { PreprocessConfig, StepSpec } from "@/lib/api";

function OptionField({
  spec,
  value,
  onChange,
}: {
  spec: StepSpec["options"][number];
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  if (spec.type === "boolean") {
    return (
      <label className="flex items-center justify-between gap-3 py-1">
        <span className="text-xs text-text">
          {spec.label}
          {spec.help ? <span className="block text-[10px] text-text-subtle">{spec.help}</span> : null}
        </span>
        <button
          type="button"
          role="switch"
          aria-checked={Boolean(value)}
          aria-label={spec.label}
          onClick={() => onChange(!value)}
          className={clsx(
            "relative h-5 w-9 shrink-0 rounded-full transition-colors duration-150",
            value ? "bg-fire-deep-orange" : "bg-border",
          )}
        >
          <span
            className={clsx(
              "absolute top-0.5 size-4 rounded-full bg-white shadow-sm transition-all duration-150",
              value ? "left-4.5" : "left-0.5",
            )}
          />
        </button>
      </label>
    );
  }

  if (spec.type === "select") {
    return (
      <label className="block py-1">
        <span className="text-xs text-text">{spec.label}</span>
        <select
          value={String(value ?? "")}
          onChange={(event) => onChange(event.target.value)}
          className="mt-1 h-8 w-full rounded-lg border border-border bg-surface px-2 text-xs"
        >
          {spec.choices?.map((choice) => (
            <option key={choice.value} value={choice.value}>
              {choice.label}
            </option>
          ))}
        </select>
      </label>
    );
  }

  return (
    <label className="block py-1">
      <span className="text-xs text-text">{spec.label}</span>
      <input
        type="number"
        step="any"
        value={String(value ?? "")}
        onChange={(event) => onChange(event.target.value === "" ? 0 : Number(event.target.value))}
        className="mt-1 h-8 w-full rounded-lg border border-border bg-surface px-2 text-xs"
      />
    </label>
  );
}

export default function ConfigStepper({
  steps,
  config,
  onChange,
}: {
  steps: StepSpec[];
  config: PreprocessConfig;
  onChange: (section: string, key: string, value: unknown) => void;
}) {
  const [openSteps, setOpenSteps] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(steps.map((step) => [step.key, step.available])),
  );

  return (
    <ol className="space-y-2">
      {steps.map((step, index) => {
        const open = openSteps[step.key] ?? false;
        return (
          <li
            key={step.key}
            className={clsx(
              "rounded-xl border border-border bg-surface",
              !step.available && "bg-surface-muted/60",
            )}
          >
            <div className="flex items-center gap-2 px-3 py-2.5">
              <span
                className={clsx(
                  "flex size-6 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold",
                  step.available ? "bg-fire-tint text-fire-deep-orange" : "bg-border text-text-subtle",
                )}
              >
                {index + 1}
              </span>
              <button
                type="button"
                onClick={() => step.available && setOpenSteps((current) => ({ ...current, [step.key]: !open }))}
                className="flex flex-1 items-center gap-2 text-left"
                aria-expanded={open}
              >
                <span className="text-sm font-medium">{step.label}</span>
                {!step.available ? (
                  <Badge tone="muted">
                    <Lock className="size-2.5" aria-hidden /> {step.note ?? "Belum aktif"}
                  </Badge>
                ) : null}
                <span className="ml-auto text-text-muted">
                  {step.available ? (
                    open ? <ChevronUp className="size-4" aria-hidden /> : <ChevronDown className="size-4" aria-hidden />
                  ) : null}
                </span>
              </button>
            </div>

            {open && step.available ? (
              <div className="border-t border-border px-3 py-2">
                <p className="mb-1 text-[11px] text-text-subtle">{step.description}</p>
                {step.options.map((option) => (
                  <OptionField
                    key={option.key}
                    spec={option}
                    value={(config[step.key] ?? {})[option.key]}
                    onChange={(value) => onChange(step.key, option.key, value)}
                  />
                ))}
              </div>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
