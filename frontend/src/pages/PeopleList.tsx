// Screen 1: the people followed, those who need attention first.
import { Mic, UserPlus } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Card, ErrorNote, LevelBadge, Loading, SyntheticBadge } from "../components/ui";
import { buttonStyles } from "../lib/styles";
import { formatDate } from "../lib/format";
import { useApi } from "../lib/useApi";

export function PeopleList() {
  const { data, error, loading, reload } = useApi(() => api.people(), []);
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">People followed</h1>
          <p className="mt-1 text-sm text-slate-600">
            Each person is compared with their own earlier sessions, never with other people.
          </p>
        </div>
        <Link to="/people/new" className={buttonStyles.primary}>
          <UserPlus aria-hidden className="size-4" /> New person
        </Link>
      </div>
      {error && <ErrorNote error={error} onRetry={reload} />}
      {loading && !data && <Loading />}
      {data && (
        <Card className="overflow-hidden p-0!">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50/70 text-xs text-slate-500">
                <tr>
                  <th className="px-6 py-3 font-medium">Name</th>
                  <th className="px-3 py-3 font-medium">Age</th>
                  <th className="px-3 py-3 font-medium">Last session</th>
                  <th className="px-3 py-3 font-medium">Sessions</th>
                  <th className="px-3 py-3 font-medium">Orientation</th>
                  <th className="px-3 py-3 font-medium">Baseline</th>
                  <th className="px-6 py-3" aria-label="Actions" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.map((person) => (
                  <tr key={person.person_id} className="hover:bg-slate-50/70">
                    <td className="px-6 py-3.5">
                      <div className="flex items-center gap-2">
                        <Link
                          to={`/people/${person.person_id}`}
                          className="font-medium text-slate-900 underline-offset-2 hover:underline"
                        >
                          {person.display_name}
                        </Link>
                        {person.synthetic && <SyntheticBadge />}
                      </div>
                    </td>
                    <td className="tabular px-3 py-3.5 text-slate-700">{person.age ?? "—"}</td>
                    <td className="px-3 py-3.5 text-slate-700">
                      {formatDate(person.last_session_at)}
                      {person.in_progress_count > 0 && (
                        <span className="ml-2 text-xs text-slate-500">processing…</span>
                      )}
                    </td>
                    <td className="tabular px-3 py-3.5 text-slate-700">
                      {person.usable_session_count} / {person.session_count}
                    </td>
                    <td className="px-3 py-3.5">
                      <LevelBadge
                        level={person.orientation_level}
                        baselineCount={person.baseline_session_count}
                        size="sm"
                      />
                    </td>
                    <td className="px-3 py-3.5 text-slate-600">
                      {person.orientation_level === "building_baseline"
                        ? `Building ${Math.min(person.baseline_session_count, 3)}/3`
                        : `${person.baseline_session_count} sessions`}
                    </td>
                    <td className="px-6 py-3.5 text-right">
                      <Link
                        to={`/people/${person.person_id}/new-session`}
                        className={buttonStyles.quiet}
                      >
                        <Mic aria-hidden className="size-4" /> New session
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
