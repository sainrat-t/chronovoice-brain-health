// Screen 2: one person, words first, numbers on demand.
import { Mic, Printer } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { ChangeFromBaselineChart, ChangeTable, FamilyCharts, MarkerCharts } from "../components/charts";
import {
  OrientationCard,
  RetoldAnecdotes,
  RiskProfileCard,
  SessionsTable,
  SummaryCard,
} from "../components/person";
import { Card, Details, ErrorNote, Loading, SyntheticBadge } from "../components/ui";
import { buttonStyles } from "../lib/styles";
import { formatDate } from "../lib/format";
import { useApi } from "../lib/useApi";

export function PersonPage() {
  const { personId = "" } = useParams();
  const { data, error, loading, reload } = useApi(() => api.person(personId), [personId]);
  if (error && !data) return <ErrorNote error={error} onRetry={reload} />;
  if (loading && !data) return <Loading />;
  if (!data) return null;

  const { person, trajectory, orientation } = data;
  const latestComparison = [...trajectory.points].reverse().find((p) => p.comparison)?.comparison;
  const summarySession = data.sessions.find(
    (session) => session.session_id === data.latest_summary?.session_id,
  );

  return (
    <div className={`space-y-6 ${loading ? "opacity-70" : ""}`}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
              {person.display_name}
            </h1>
            {person.synthetic && <SyntheticBadge />}
          </div>
          <p className="mt-1 text-sm text-slate-600">
            {data.age !== null && `${data.age} years · `}English · first session{" "}
            {formatDate(data.first_session_at)}
          </p>
          {person.summary && <p className="mt-1 text-sm text-slate-500">{person.summary}</p>}
        </div>
        <div className="flex gap-2">
          <Link to={`/people/${person.person_id}/report`} className={buttonStyles.secondary}>
            <Printer aria-hidden className="size-4" /> Report
          </Link>
          <Link to={`/people/${person.person_id}/new-session`} className={buttonStyles.primary}>
            <Mic aria-hidden className="size-4" /> New session
          </Link>
        </div>
      </div>

      <OrientationCard orientation={orientation} />

      <Card
        title="Change from baseline"
        aside={
          <span className="text-xs text-slate-500">
            In units of the person's usual variability · 0 means as usual · higher points toward
            decline
          </span>
        }
      >
        <ChangeFromBaselineChart
          points={trajectory.points}
          uncertainty={latestComparison?.uncertainty ?? null}
        />
        <Details summary="Details: values by session">
          <ChangeTable points={trajectory.points} />
        </Details>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <SummaryCard
            personId={person.person_id}
            summary={data.latest_summary}
            specs={trajectory.marker_specs}
            sessionDate={summarySession?.recorded_at}
            onReviewed={reload}
          />
          <Card title="Sub-scores">
            <FamilyCharts points={trajectory.points} />
          </Card>
          <Card title="Markers">
            <MarkerCharts points={trajectory.points} specs={trajectory.marker_specs} />
          </Card>
        </div>
        <div className="space-y-6">
          <RiskProfileCard profile={data.risk_profile} />
          <RetoldAnecdotes anecdotes={data.retold_anecdotes} />
        </div>
      </div>

      <Card title="Sessions">
        <SessionsTable sessions={data.sessions} />
      </Card>
    </div>
  );
}
