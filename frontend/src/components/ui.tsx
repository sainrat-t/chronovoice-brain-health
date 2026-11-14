// Small shared pieces of the interface.
import { AlertCircle, ChevronRight, FlaskConical, LoaderCircle } from "lucide-react";
import { useState, type ReactNode } from "react";
import type { OrientationLevel } from "../api/types";
import { LEVELS } from "../lib/levels";

export function Card({
  title,
  aside,
  children,
  className = "",
}: {
  title?: ReactNode;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-2xl border border-slate-200/80 bg-white p-6 shadow-[0_1px_2px_rgba(15,23,42,0.04)] ${className}`}
    >
      {(title || aside) && (
        <header className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
          {title && <h2 className="text-base font-semibold text-slate-800">{title}</h2>}
          {aside}
        </header>
      )}
      {children}
    </section>
  );
}

export function LevelBadge({
  level,
  baselineCount,
  size = "md",
}: {
  level: OrientationLevel;
  baselineCount?: number;
  size?: "sm" | "md" | "lg";
}) {
  const style = LEVELS[level];
  const Icon = style.icon;
  const label =
    level === "building_baseline" && baselineCount !== undefined
      ? `${style.label} ${Math.min(baselineCount, 3)}/3`
      : style.label;
  const sizes = {
    sm: "gap-1 px-2 py-0.5 text-xs",
    md: "gap-1.5 px-2.5 py-1 text-sm",
    lg: "gap-2 px-3 py-1.5 text-base",
  };
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded-full font-medium ring-1 ring-inset ${style.badge} ${sizes[size]}`}
    >
      <Icon aria-hidden className={size === "lg" ? "size-5" : "size-4"} strokeWidth={2} />
      {label}
    </span>
  );
}

export function SyntheticBadge() {
  return (
    <span className="inline-flex items-center rounded-md bg-slate-100 px-1.5 py-0.5 text-xs font-medium text-slate-600 ring-1 ring-slate-200 ring-inset">
      Synthetic
    </span>
  );
}

export function ExperimentalBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-md bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-600 ring-1 ring-slate-300 ring-inset ring-dashed">
      <FlaskConical aria-hidden className="size-3.5" />
      Experimental, not in the index
    </span>
  );
}

/** Numbers on demand: words first, figures in a panel the reader opens. */
export function Details({ summary = "Details", children }: { summary?: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-4 border-t border-slate-100 pt-3">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="inline-flex items-center gap-1 text-sm font-medium text-slate-600 hover:text-slate-900"
      >
        <ChevronRight
          aria-hidden
          className={`size-4 transition-transform ${open ? "rotate-90" : ""}`}
        />
        {summary}
      </button>
      {open && <div className="mt-3">{children}</div>}
    </div>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <p className="flex items-center gap-2 py-10 text-sm text-slate-500" role="status">
      <LoaderCircle aria-hidden className="size-4 animate-spin" />
      {label}…
    </p>
  );
}

export function ErrorNote({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-xl border border-terra-200 bg-terra-50 p-4 text-sm text-terra-800"
    >
      <AlertCircle aria-hidden className="mt-0.5 size-4 shrink-0" />
      <div className="flex-1">{error.message}</div>
      {onRetry && (
        <button type="button" onClick={onRetry} className="font-medium underline">
          Try again
        </button>
      )}
    </div>
  );
}
