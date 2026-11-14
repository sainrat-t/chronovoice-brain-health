// Types of the API, generated from the backend's OpenAPI description (schema.d.ts):
// they mirror backend/app/api/models.py and backend/app/schemas.py field for field.
// Regenerate after a backend change: `uv run python -m scripts.export_openapi` in
// backend/, then `npm run gen:api` here.
import type { components } from "./schema";

type Schemas = components["schemas"];

export type AnnotatedTranscript = Schemas["AnnotatedTranscript"];
export type ClinicalSummaryReport = Schemas["ClinicalSummaryReport"];
export type Finding = Schemas["Finding"];
export type LongitudinalComparisonResult = Schemas["LongitudinalComparisonResult"];
export type MarkerDeviation = Schemas["MarkerDeviation"];
export type MarkerId = Schemas["MarkerId"];
export type MarkerSpec = Schemas["MarkerSpec"];
export type OrientationLevel = Schemas["OrientationLevel"];
export type OrientationView = Schemas["OrientationView"];
export type Person = Schemas["Person"];
export type PersonCreate = Schemas["PersonCreate"];
export type PersonDetail = Schemas["PersonDetail"];
export type PersonSummary = Schemas["PersonSummary"];
export type Prompt = Schemas["Prompt"];
export type QualityReason = Schemas["QualityReason"];
export type QualityReport = Schemas["QualityReport"];
export type QualityStatus = Schemas["QualityStatus"];
export type RecordingContext = Schemas["RecordingContext"];
export type RetoldAnecdote = Schemas["RetoldAnecdote"];
export type RiskProfile = Schemas["RiskProfile"];
export type SessionAccepted = Schemas["SessionAccepted"];
export type SessionDetail = Schemas["SessionDetail"];
export type SessionItem = Schemas["SessionItem"];
export type SessionMetrics = Schemas["SessionMetrics"];
export type SessionStatus = Schemas["SessionStatus"];
export type SessionStatusView = Schemas["SessionStatusView"];
export type StudyRef = Schemas["StudyRef"];
export type Trajectory = Schemas["Trajectory"];
export type TrajectoryPoint = Schemas["TrajectoryPoint"];
export type TranscriptItem = Schemas["TranscriptItem"];
export type TranscriptTurn = Schemas["TranscriptTurn"];
export type Uncertainty = Schemas["Uncertainty"];

/**
 * The `metadata` part of a session upload (backend SessionUpload). It travels as a
 * JSON form field next to the audio, so it is not in the generated schemas.
 */
export interface SessionUpload {
  consent: true;
  context: RecordingContext;
  prompt_id: string | null;
  recorded_at?: string;
  task_type?: "life_story";
}

/** Mirrors backend/app/schemas.py: a session is "in deviation" from this many markers. */
export const MIN_SIGNIFICANT_MARKERS = 2;
/** Mirrors backend/app/schemas.py: no orientation level below this many baseline sessions. */
export const MIN_BASELINE_SESSIONS = 3;
