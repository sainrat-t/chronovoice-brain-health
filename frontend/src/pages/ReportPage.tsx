// Screen 5: the summary on one A4 page, for printing.
import { ArrowLeft, Printer } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { ErrorNote, LevelBadge, Loading } from "../components/ui";
import { buttonStyles } from "../lib/styles";
import { formatDate, formatStudy } from "../lib/format";
import { useApi } from "../lib/useApi";

export function ReportPage() {
  const { personId = "" } = useParams();
  const { data, error, reload } = useApi(() => api.person(personId), [personId]);
  if (error) return <ErrorNote error={error} onRetry={reload} />;
  if (!data) return <Loading />;
  const summary = data.latest_summary;
  const session = data.sessions.find((s) => s.session_id === summary?.session_id);
  const labels = new Map(data.trajectory.marker_specs.map((spec) => [spec.marker, spec.label]));

  return (
    <div className="space-y-4">
      <div className="no-print flex justify-between">
        <Link to={`/people/${personId}`} className={buttonStyles.quiet}>
          <ArrowLeft aria-hidden className="size-4" /> Back
        </Link>
        <button type="button" className={buttonStyles.primary} onClick={() => window.print()}>
          <Printer aria-hidden className="size-4" /> Print
        </button>
      </div>
      <article className="print-page mx-auto max-w-[210mm] space-y-6 rounded-2xl border border-slate-200 bg-white p-12 text-[14px] leading-relaxed shadow-sm">
        <header className="flex items-start justify-between border-b border-slate-200 pb-4">
          <div>
            <p className="text-xs font-semibold tracking-wide text-slate-500 uppercase">
              ChronoVoice Brain · speech follow-up summary
            </p>
            <h1 className="mt-1 text-xl font-semibold text-slate-900">
              {data.person.display_name}
            </h1>
            <p className="text-slate-600">
              {data.age !== null && `${data.age} years · `}Session of {formatDate(session?.recorded_at)}
              {data.person.synthetic && " · synthetic demonstration data"}
            </p>
          </div>
          {data.orientation && (
            <LevelBadge
              level={data.orientation.level}
              baselineCount={data.orientation.uncertainty.baseline_session_count}
            />
          )}
        </header>

        {!summary ? (
          <p className="text-slate-600">No summary yet.</p>
        ) : (
          <>
            <section>
              <h2 className="text-base font-semibold text-slate-900">
                {summary.clinician_summary.headline}
              </h2>
              {data.orientation && (
                <p className="mt-1 text-slate-700">{data.orientation.rule_text}</p>
              )}
              <p className="mt-2 font-medium text-slate-900">
                Suggested action: {data.orientation?.action_text}
              </p>
            </section>
            <section>
              <h3 className="mb-2 text-sm font-semibold text-slate-800">Findings</h3>
              <ul className="list-disc space-y-2 pl-5 text-slate-800">
                {summary.clinician_summary.findings.map((finding, index) => (
                  <li key={index}>
                    {finding.text}{" "}
                    <span className="text-xs text-slate-500">
                      ({finding.marker_ids.map((m) => labels.get(m) ?? m).join(", ")}
                      {finding.study_refs.length > 0 &&
                        `; ${finding.study_refs.map(formatStudy).join(", ")}`}
                      )
                    </span>
                  </li>
                ))}
              </ul>
            </section>
            <section>
              <h3 className="mb-1 text-sm font-semibold text-slate-800">Uncertainty</h3>
              <p className="text-slate-700">{summary.clinician_summary.uncertainty_statement}</p>
            </section>
            <section>
              <h3 className="mb-1 text-sm font-semibold text-slate-800">For the person</h3>
              <p className="text-slate-700">{summary.person_explanation}</p>
            </section>
            <section className="text-slate-700">
              {summary.review?.status === "validated"
                ? `Reviewed and validated by ${summary.review.reviewed_by} on ${formatDate(summary.review.reviewed_at)}.`
                : "Draft: not yet reviewed by a clinician."}
            </section>
          </>
        )}
        <footer className="border-t border-slate-200 pt-3 text-xs text-slate-500">
          Screening support only, not a diagnosis. The measures compare the person with their own
          earlier sessions; many everyday factors can move them.
        </footer>
      </article>
    </div>
  );
}
