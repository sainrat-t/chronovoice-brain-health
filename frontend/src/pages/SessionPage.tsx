// Screen 3: one session, its highlighted transcript and its markers.
import { ArrowLeft, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { MarkerSpec, SessionDetail } from "../api/types";
import {
  CompareMarkers,
  MarkersTable,
  QualityPanel,
  TranscriptLegend,
  TranscriptView,
} from "../components/session";
import { Card, ErrorNote, LevelBadge, Loading } from "../components/ui";
import { buttonStyles } from "../lib/styles";
import { formatChange, formatDateTime } from "../lib/format";
import { IN_PROGRESS, STATUS_LABELS } from "../lib/levels";
import { useApi } from "../lib/useApi";

function ContextList({ detail }: { detail: SessionDetail }) {
  const context = detail.metadata.context ?? {};
  const rows: [string, string | null | undefined][] = [
    ["Sleep last night", context.sleep],
    ["Fatigue", context.fatigue === null || context.fatigue === undefined ? null : context.fatigue ? "yes" : "no"],
    [
      "Acute illness",
      context.acute_illness === null || context.acute_illness === undefined
        ? null
        : context.acute_illness
          ? "yes"
          : "no",
    ],
    [
      "New treatment",
      context.new_medication === null || context.new_medication === undefined
        ? null
        : context.new_medication
          ? "yes"
          : "no",
    ],
    ["Mood", context.mood],
  ];
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm text-slate-600">
      <dt>Theme</dt>
      <dd className="text-right text-slate-800">{detail.prompt?.theme ?? "—"}</dd>
      {rows.map(([label, value]) => (
        <div key={label} className="contents">
          <dt>{label}</dt>
          <dd className="text-right text-slate-800">{value ?? "not entered"}</dd>
        </div>
      ))}
    </dl>
  );
}

function Comparison({
  personId,
  current,
  specs,
}: {
  personId: string;
  current: SessionDetail;
  specs: readonly MarkerSpec[];
}) {
  const person = useApi(() => api.person(personId), [personId]);
  const [referenceId, setReferenceId] = useState("");
  const reference = useApi(
    () => (referenceId ? api.session(referenceId) : Promise.resolve(null)),
    [referenceId],
  );
  const options = (person.data?.sessions ?? []).filter(
    (s) => s.session_id !== current.session.session_id && s.quality_status !== "rejected",
  );
  const baselineIds = new Set(current.comparison?.baseline?.session_ids ?? []);
  return (
    <Card title="Compare with another session">
      <label className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
        Reference session
        <select
          value={referenceId}
          onChange={(event) => setReferenceId(event.target.value)}
          className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
        >
          <option value="">Choose…</option>
          {options.map((s) => (
            <option key={s.session_id} value={s.session_id}>
              {formatDateTime(s.recorded_at)} · {s.theme ?? "no theme"}
              {baselineIds.has(s.session_id) ? " · baseline" : ""}
            </option>
          ))}
        </select>
      </label>
      {reference.data && (
        <div className="mt-5 space-y-6">
          <CompareMarkers
            current={current.metrics}
            reference={reference.data.metrics}
            specs={specs}
          />
          <div className="grid gap-6 lg:grid-cols-2">
            {[current, reference.data].map((detail, index) => (
              <div key={detail.session.session_id} className="min-w-0">
                <p className="mb-2 text-sm font-semibold text-slate-800">
                  {index === 0 ? "This session" : "Reference"} ·{" "}
                  {formatDateTime(detail.session.recorded_at)}
                </p>
                {detail.transcript && (
                  <div className="max-h-[28rem] overflow-y-auto rounded-lg border border-slate-100 p-3">
                    <TranscriptView transcript={detail.transcript} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

export function SessionPage() {
  const { sessionId = "" } = useParams();
  const { data, error, loading, reload } = useApi(() => api.session(sessionId), [sessionId]);
  const specs = useApi(
    () =>
      data ? api.person(data.session.person_id).then((p) => p.trajectory.marker_specs) : Promise.resolve([]),
    [data?.session.person_id],
  );
  const [retryError, setRetryError] = useState<Error | null>(null);

  // While the session is being processed, follow it every 2 seconds.
  const inProgress = data ? IN_PROGRESS.has(data.session.status) : false;
  useEffect(() => {
    if (!inProgress) return;
    const timer = window.setInterval(reload, 2000);
    return () => window.clearInterval(timer);
  }, [inProgress, reload]);

  if (error && !data) return <ErrorNote error={error} onRetry={reload} />;
  if (loading && !data) return <Loading />;
  if (!data) return null;
  const { session, comparison } = data;
  const markerSpecs = specs.data ?? [];

  async function retry() {
    setRetryError(null);
    try {
      await api.retrySession(sessionId);
      reload();
    } catch (reason) {
      setRetryError(reason instanceof Error ? reason : new Error(String(reason)));
    }
  }

  return (
    <div className="space-y-6">
      <Link to={`/people/${session.person_id}`} className={buttonStyles.quiet}>
        <ArrowLeft aria-hidden className="size-4" /> Back to the person
      </Link>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            Session of {formatDateTime(session.recorded_at)}
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            {data.prompt ? `“${data.prompt.question}”` : "No opening question recorded"}
            {session.source === "integration" && " · sent by another application"}
          </p>
        </div>
        {comparison && (
          <div className="text-right">
            <LevelBadge
              level={comparison.orientation.level}
              baselineCount={comparison.uncertainty.baseline_session_count}
            />
            {comparison.change_index && (
              <p className="tabular mt-1.5 text-sm text-slate-600">
                Change from baseline {formatChange(comparison.change_index.value)} ·{" "}
                {comparison.change_index.significant_markers.length} of{" "}
                {comparison.change_index.tested_markers.length} markers beyond range
              </p>
            )}
          </div>
        )}
      </div>

      {inProgress && (
        <Card>
          <p className="text-sm text-slate-700" role="status">
            {STATUS_LABELS[session.status]}… this page updates by itself.
          </p>
        </Card>
      )}
      {session.status === "failed" && (
        <Card>
          <p className="text-sm text-terra-800">This session could not be processed: {data.error}</p>
          <button type="button" className={`${buttonStyles.secondary} mt-3`} onClick={retry}>
            <RotateCcw aria-hidden className="size-4" /> Try again
          </button>
          {retryError && (
            <div className="mt-3">
              <ErrorNote error={retryError} />
            </div>
          )}
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Transcript" className="lg:col-span-2" aside={<TranscriptLegend />}>
          {data.transcript ? (
            <TranscriptView transcript={data.transcript} />
          ) : (
            <p className="text-sm text-slate-500">
              No transcript yet. The audio itself is never kept.
            </p>
          )}
        </Card>
        <div className="space-y-6">
          <Card title="Quality">
            <QualityPanel quality={data.quality} />
          </Card>
          <Card title="Context">
            <ContextList detail={data} />
          </Card>
        </div>
      </div>

      <Card title="Markers">
        <MarkersTable metrics={data.metrics} comparison={comparison} specs={markerSpecs} />
      </Card>

      {data.metrics && (
        <Comparison personId={session.person_id} current={data} specs={markerSpecs} />
      )}
    </div>
  );
}
