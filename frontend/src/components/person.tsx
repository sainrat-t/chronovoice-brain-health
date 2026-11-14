// Sections of the person page (docs/specs/clinician-ui.md, screen 2).
import { BadgeCheck, CircleSlash, FileText, Lock, MessageSquareQuote, Printer } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type {
  ClinicalSummaryReport,
  MarkerSpec,
  OrientationView,
  RetoldAnecdote,
  RiskProfile,
  SessionItem,
} from "../api/types";
import { formatDate, formatDuration, formatNumber, formatStudy, plural } from "../lib/format";
import { IN_PROGRESS, LEVELS, QUALITY_LABELS, STATUS_LABELS } from "../lib/levels";
import { Card, ErrorNote, ExperimentalBadge, LevelBadge } from "./ui";
import { buttonStyles } from "../lib/styles";

export function UncertaintyLine({ orientation }: { orientation: OrientationView }) {
  const { uncertainty } = orientation;
  const range = uncertainty.baseline_change_index_range;
  return (
    <p className="text-sm text-slate-600">
      Personal baseline: {plural(uncertainty.baseline_session_count, "session")}
      {range && (
        <>
          {" "}
          (their changes ranged from {formatNumber(range[0], 1)} to {formatNumber(range[1], 1)}{" "}
          SD)
        </>
      )}
      {" · "}Last session quality: {QUALITY_LABELS[uncertainty.quality_status].toLowerCase()}
    </p>
  );
}

export function OrientationCard({ orientation }: { orientation: OrientationView | null }) {
  if (!orientation) {
    return (
      <Card title="Orientation">
        <LevelBadge level="building_baseline" baselineCount={0} size="lg" />
        <p className="mt-3 text-sm text-slate-600">
          No session yet. The first three usable sessions build the personal baseline; no
          signal is shown before it exists.
        </p>
      </Card>
    );
  }
  const style = LEVELS[orientation.level];
  return (
    <section
      className="rounded-2xl border border-l-4 border-slate-200/80 bg-white p-6 shadow-[0_1px_2px_rgba(15,23,42,0.04)]"
      style={{ borderLeftColor: style.tone }}
    >
      <div>
        <div className="space-y-3">
          <LevelBadge
            level={orientation.level}
            baselineCount={orientation.uncertainty.baseline_session_count}
            size="lg"
          />
          <p className="max-w-2xl text-[15px] leading-relaxed text-slate-800">
            {orientation.rule_text}
          </p>
          <p className="text-[15px] font-medium text-slate-900">
            Suggested action: {orientation.action_text}
          </p>
          <UncertaintyLine orientation={orientation} />
          {orientation.adverse_context.length > 0 && (
            <p className="text-sm text-slate-600">
              Context reported for the last session: {orientation.adverse_context.join(", ")}.
              It makes that session less reliable.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

export function SummaryCard({
  personId,
  summary,
  specs,
  sessionDate,
  onReviewed,
}: {
  personId: string;
  summary: ClinicalSummaryReport | null;
  sessionDate?: string;
  specs: readonly MarkerSpec[];
  onReviewed: () => void;
}) {
  const [name, setName] = useState(() => localStorage.getItem("chronovoice.reviewer") ?? "");
  const [error, setError] = useState<Error | null>(null);
  const [saving, setSaving] = useState(false);
  if (!summary) {
    return (
      <Card title="Summary">
        <p className="text-sm text-slate-500">No summary yet: it is written after each session.</p>
      </Card>
    );
  }
  const labels = new Map(specs.map((spec) => [spec.marker, spec.label]));
  const clinician = summary.clinician_summary;
  const validated = summary.review?.status === "validated";

  async function validate() {
    setSaving(true);
    setError(null);
    try {
      localStorage.setItem("chronovoice.reviewer", name.trim());
      await api.reviewSummary(personId, name.trim());
      onReviewed();
    } catch (reason) {
      setError(reason instanceof Error ? reason : new Error(String(reason)));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card
      title="Summary"
      aside={
        <div className="no-print flex items-center gap-2">
          <Link to={`/people/${personId}/report`} className={buttonStyles.quiet}>
            <Printer aria-hidden className="size-4" /> Print
          </Link>
        </div>
      }
    >
      <p className="text-xs text-slate-500">
        {sessionDate && `Session of ${formatDate(sessionDate)} · `}
        {summary.generation_mode === "llm"
          ? `Written by a language model (${summary.model_id}), checked against the measurements.`
          : "Fixed wording built from the measurements."}
      </p>
      <h3 className="mt-2 text-lg font-semibold text-slate-900">{clinician.headline}</h3>
      <ul className="mt-4 space-y-4">
        {clinician.findings.map((finding, index) => (
          <li key={index} className="flex gap-3">
            <span
              aria-hidden
              className={`mt-2 size-2 shrink-0 rounded-full ${
                finding.beyond_usual_range ? "bg-terra-500" : "bg-sage-500"
              }`}
            />
            <div className="space-y-1.5">
              <p className="text-[15px] leading-relaxed text-slate-800">{finding.text}</p>
              <div className="flex flex-wrap gap-1.5">
                {finding.marker_ids.map((marker) => (
                  <span
                    key={marker}
                    className="rounded-md bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600"
                  >
                    {labels.get(marker) ?? marker}
                  </span>
                ))}
                {finding.study_refs.map((ref) => (
                  <span key={ref} className="px-1 text-xs text-slate-500 italic">
                    {formatStudy(ref)}
                  </span>
                ))}
              </div>
              {finding.passages.map((passage) => (
                <blockquote
                  key={passage}
                  className="flex gap-2 border-l-2 border-slate-200 pl-3 text-sm text-slate-600"
                >
                  <MessageSquareQuote aria-hidden className="mt-0.5 size-3.5 shrink-0" />“{passage}”
                </blockquote>
              ))}
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-5 rounded-lg bg-slate-50 p-3 text-sm leading-relaxed text-slate-600">
        {clinician.uncertainty_statement}
      </p>

      <div className="mt-5 rounded-xl border border-sage-200 bg-sage-50 p-4">
        <p className="flex items-center gap-1.5 text-xs font-semibold tracking-wide text-sage-800 uppercase">
          <FileText aria-hidden className="size-3.5" /> For the person, in plain words
        </p>
        <p className="mt-2 text-[15px] leading-relaxed text-slate-800">
          {summary.person_explanation}
        </p>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-slate-100 pt-4">
        {validated ? (
          <p className="flex items-center gap-1.5 text-sm font-medium text-sage-800">
            <BadgeCheck aria-hidden className="size-4" />
            Validated by {summary.review?.reviewed_by} on {formatDate(summary.review?.reviewed_at)}
          </p>
        ) : (
          <>
            <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
              Draft
            </span>
            <label className="no-print flex items-center gap-2 text-sm text-slate-600">
              Your name
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="w-48 rounded-md border border-slate-300 px-2 py-1 text-sm"
                placeholder="e.g. Dr Amal Nasser"
              />
            </label>
            <button
              type="button"
              className={`${buttonStyles.primary} no-print`}
              disabled={!name.trim() || saving}
              onClick={validate}
            >
              <BadgeCheck aria-hidden className="size-4" />
              Reviewed and validated
            </button>
          </>
        )}
      </div>
      {error && (
        <div className="mt-3">
          <ErrorNote error={error} />
        </div>
      )}
    </Card>
  );
}

export function RetoldAnecdotes({ anecdotes }: { anecdotes: readonly RetoldAnecdote[] }) {
  return (
    <Card title="Life story" aside={<ExperimentalBadge />}>
      <p className="mb-4 text-sm text-slate-600">
        Anecdotes told again, as found by a language model. They are shown for context and
        never enter the change index.
      </p>
      {anecdotes.length === 0 ? (
        <p className="text-sm text-slate-500">No anecdote told again so far.</p>
      ) : (
        <ul className="space-y-4">
          {anecdotes.map((anecdote, index) => (
            <li key={index} className="rounded-xl border border-dashed border-slate-300 p-4">
              <p className="text-sm font-medium text-slate-800">{anecdote.episode_summary}</p>
              <p className="mt-1 text-xs text-slate-500">
                <Link className="underline" to={`/sessions/${anecdote.session_id}`}>
                  {formatDate(anecdote.recorded_at)}
                </Link>
                {anecdote.previous_session_id ? (
                  <>
                    {" · first told on "}
                    <Link className="underline" to={`/sessions/${anecdote.previous_session_id}`}>
                      {formatDate(anecdote.previous_recorded_at)}
                    </Link>
                  </>
                ) : (
                  " · told twice in the same session"
                )}
                {" · "}
                {anecdote.self_flagged ? "the person said so" : "not mentioned by the person"}
              </p>
              {anecdote.acknowledgement_quote && (
                <p className="mt-2 text-sm text-slate-600 italic">
                  “{anecdote.acknowledgement_quote}”
                </p>
              )}
              {anecdote.quoted_passages.map((passage) => (
                <blockquote
                  key={passage}
                  className="mt-2 border-l-2 border-slate-200 pl-3 text-sm text-slate-600"
                >
                  “{passage}”
                </blockquote>
              ))}
              <p className="mt-2 text-xs text-slate-500">{anecdote.rationale}</p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function RiskProfileCard({ profile }: { profile: RiskProfile | null }) {
  return (
    <Card
      title="Risk profile"
      aside={<span className="text-xs text-slate-500">Shared with consent · read only</span>}
    >
      <p className="mb-3 text-sm text-slate-600">
        Shown next to the speech measures, never mixed into them.
      </p>
      {!profile ? (
        <p className="text-sm text-slate-500">No risk profile shared.</p>
      ) : (
        <dl className="divide-y divide-slate-100 text-sm">
          {profile.entries.map((entry) => (
            <div key={entry.factor} className="flex justify-between gap-4 py-2">
              <dt className="text-slate-500">{entry.factor}</dt>
              <dd className="text-right text-slate-800">
                {entry.shared ? (
                  entry.value
                ) : (
                  <span className="inline-flex items-center gap-1 text-slate-500">
                    <Lock aria-hidden className="size-3.5" /> Not shared
                  </span>
                )}
              </dd>
            </div>
          ))}
        </dl>
      )}
      <p className="mt-4 flex items-start gap-2 text-xs text-slate-500">
        <CircleSlash aria-hidden className="mt-0.5 size-3.5 shrink-0" />
        Prevention suggestions will come from a fixed, sourced list (Lancet Commission 2024);
        that list is still being reviewed, so none are shown yet.
      </p>
    </Card>
  );
}

export function SessionsTable({ sessions }: { sessions: readonly SessionItem[] }) {
  if (sessions.length === 0) {
    return <p className="text-sm text-slate-500">No session recorded yet.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="text-xs text-slate-500">
          <tr>
            <th className="py-2 pr-4 font-medium">Date</th>
            <th className="py-2 pr-4 font-medium">Theme</th>
            <th className="py-2 pr-4 font-medium">Quality</th>
            <th className="py-2 pr-4 font-medium">Speech</th>
            <th className="py-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {[...sessions].reverse().map((session) => (
            <tr key={session.session_id} className="hover:bg-slate-50">
              <td className="py-2 pr-4">
                <Link
                  className="font-medium text-slate-800 underline-offset-2 hover:underline"
                  to={`/sessions/${session.session_id}`}
                >
                  {formatDate(session.recorded_at)}
                </Link>
              </td>
              <td className="py-2 pr-4 text-slate-700">{session.theme ?? "—"}</td>
              <td className="py-2 pr-4 text-slate-700">
                {session.quality_status ? QUALITY_LABELS[session.quality_status] : "—"}
              </td>
              <td className="tabular py-2 pr-4 text-slate-700">
                {formatDuration(session.speaking_time_s)}
              </td>
              <td className="py-2 text-slate-700">
                {IN_PROGRESS.has(session.status) ? (
                  <span className="text-slate-500">{STATUS_LABELS[session.status]}…</span>
                ) : (
                  STATUS_LABELS[session.status]
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
