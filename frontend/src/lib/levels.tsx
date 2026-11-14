// Orientation levels and session statuses: colour always comes with an icon and words.
import {
  CircleCheck,
  CircleDashed,
  Eye,
  Stethoscope,
  type LucideIcon,
} from "lucide-react";
import type { OrientationLevel, QualityStatus, SessionStatus } from "../api/types";

interface LevelStyle {
  label: string;
  icon: LucideIcon;
  badge: string;
  /** Chart and dot colour for this level. */
  tone: string;
}

export const LEVELS: Record<OrientationLevel, LevelStyle> = {
  review_recommended: {
    label: "Review recommended",
    icon: Stethoscope,
    badge: "bg-terra-100 text-terra-800 ring-terra-200",
    tone: "#b9522c",
  },
  monitor: {
    label: "Signals to monitor",
    icon: Eye,
    badge: "bg-terra-50 text-terra-700 ring-terra-200",
    tone: "#e0a080",
  },
  stable: {
    label: "Within usual range",
    icon: CircleCheck,
    badge: "bg-sage-100 text-sage-800 ring-sage-200",
    tone: "#5e9384",
  },
  building_baseline: {
    label: "Building baseline",
    icon: CircleDashed,
    badge: "bg-slate-100 text-slate-700 ring-slate-200",
    tone: "#64748b",
  },
};

export const QUALITY_LABELS: Record<QualityStatus, string> = {
  usable: "Usable",
  partial: "Partial",
  rejected: "Rejected",
};

export const STATUS_LABELS: Record<SessionStatus, string> = {
  received: "Received",
  transcribing: "Transcribing",
  analysing: "Analysing",
  summarising: "Writing summary",
  done: "Done",
  rejected: "Rejected",
  failed: "Failed",
};

export const IN_PROGRESS: ReadonlySet<SessionStatus> = new Set([
  "received",
  "transcribing",
  "analysing",
  "summarising",
]);

export const QUALITY_REASON_TEXT: Record<string, string> = {
  no_target_speech: "No speech from the person could be found.",
  language_mismatch: "The recording is not in the person's language.",
  unreadable_audio: "The audio could not be read.",
  too_few_words: "Fewer than 150 words from the person.",
  too_short: "Less than 2 minutes of speech from the person.",
  low_confidence: "The transcription is uncertain (low confidence).",
};
