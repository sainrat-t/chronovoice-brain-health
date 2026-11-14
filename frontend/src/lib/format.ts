// Display helpers: dates, durations, numbers, study references.
import type { StudyRef } from "../api/types";

const dateFormat = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
});
const shortDateFormat = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" });
const dateTimeFormat = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

export const formatDate = (iso: string | null | undefined): string =>
  iso ? dateFormat.format(new Date(iso)) : "—";

export const formatShortDate = (time: number | string): string =>
  shortDateFormat.format(new Date(time));

export const formatDateTime = (iso: string | null | undefined): string =>
  iso ? dateTimeFormat.format(new Date(iso)) : "—";

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return "—";
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return minutes ? `${minutes} min ${String(rest).padStart(2, "0")} s` : `${rest} s`;
}

export function formatClock(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
}

export function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString("en-GB", { maximumFractionDigits: digits });
}

/** Change from baseline, in units of the person's own variability. */
export function formatChange(value: number): string {
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${Math.abs(value).toFixed(1)} SD`;
}

// First author and year of each study note (docs/discovery/studies/), without "et al."
// so that no co-authorship is claimed from memory.
const STUDY_NAMES: Record<StudyRef, string> = {
  "01-snowdon-1996": "Snowdon 1996",
  "02-fraser-2016": "Fraser 2016",
  "03-garrard-2005": "Garrard 2005",
  "04-agbavor-2022": "Agbavor 2022",
  "05-de-la-fuente-garcia-2020": "de la Fuente Garcia 2020",
  "06-pistono-2016": "Pistono 2016",
  "07-murphy-2008": "Murphy 2008",
  "08-mueller-2018": "Mueller 2018",
  "09-robin-2023": "Robin 2023",
  "10-kemper-2001": "Kemper 2001",
};

export const formatStudy = (ref: StudyRef): string => STUDY_NAMES[ref];

export function plural(count: number, one: string, many = `${one}s`): string {
  return `${count} ${count === 1 ? one : many}`;
}
