// Pieces of the session detail screen (docs/specs/clinician-ui.md, screen 3).
import type {
  AnnotatedTranscript,
  LongitudinalComparisonResult,
  MarkerSpec,
  QualityReport,
  SessionMetrics,
  TranscriptItem,
} from "../api/types";
import { DECLINE } from "../lib/decline";
import { formatDuration, formatNumber } from "../lib/format";
import { QUALITY_LABELS, QUALITY_REASON_TEXT } from "../lib/levels";

export function TranscriptLegend() {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-slate-600">
      <li>
        <span className="rounded bg-terra-100 px-1 text-terra-800">um</span> hesitation
      </li>
      <li>
        <span className="underline decoration-terra-500 decoration-2 underline-offset-4">
          the the
        </span>{" "}
        repetition
      </li>
      <li>
        <span className="text-terra-700 line-through decoration-terra-300">w-</span> cut-off word
      </li>
      <li>
        <span className="rounded bg-slate-100 px-1 text-slate-600">‖ 0.8 s</span> pause
      </li>
      <li>
        <span className="text-slate-400">grey</span> other speaker
      </li>
      <li>
        <span className="text-slate-500 italic">(laughs)</span> sound
      </li>
    </ul>
  );
}

function Item({ item, tracked }: { item: TranscriptItem; tracked: boolean }) {
  if (item.kind === "pause") {
    const seconds = item.end_s - item.start_s;
    return (
      <span
        className="tabular mx-0.5 rounded bg-slate-100 px-1 text-[11px] text-slate-600"
        title={item.between_utterances ? "Pause between sentences" : "Pause within a sentence"}
      >
        ‖ {seconds.toFixed(1)} s
      </span>
    );
  }
  if (item.kind === "audio_event") {
    return <span className="text-slate-500 italic">{item.text}</span>;
  }
  if (!tracked) return <span>{item.text}</span>;
  const classes = [
    item.kind === "filler" ? "rounded bg-terra-100 px-0.5 text-terra-800" : "",
    item.kind === "cut_off" ? "text-terra-700 line-through decoration-terra-300" : "",
    item.repeated ? "underline decoration-terra-500 decoration-2 underline-offset-4" : "",
  ]
    .filter(Boolean)
    .join(" ");
  return <span className={classes}>{item.text}</span>;
}

export function TranscriptView({ transcript }: { transcript: AnnotatedTranscript }) {
  return (
    <div className="space-y-3 text-[15px] leading-8">
      {transcript.turns.map((turn, index) => (
        <p
          key={index}
          className={turn.is_tracked_speaker ? "text-slate-800" : "text-sm leading-6 text-slate-400"}
        >
          {turn.items.map((item, position) => (
            <span key={position}>
              {position > 0 && " "}
              <Item item={item} tracked={turn.is_tracked_speaker} />
            </span>
          ))}
        </p>
      ))}
    </div>
  );
}

export function MarkersTable({
  metrics,
  comparison,
  specs,
}: {
  metrics: SessionMetrics | null;
  comparison: LongitudinalComparisonResult | null;
  specs: readonly MarkerSpec[];
}) {
  if (!metrics) return <p className="text-sm text-slate-500">No markers for this session.</p>;
  const deviations = new Map((comparison?.markers ?? []).map((m) => [m.marker, m]));
  return (
    <div className="overflow-x-auto">
      <table className="tabular w-full text-left text-sm">
        <thead className="text-xs text-slate-500">
          <tr>
            <th className="py-2 pr-3 font-medium">Marker</th>
            <th className="py-2 pr-3 text-right font-medium">This session</th>
            <th className="py-2 pr-3 text-right font-medium">Baseline mean ± SD</th>
            <th className="py-2 pr-3 text-right font-medium">t (toward decline)</th>
            <th className="py-2 pr-3 font-medium">Beyond usual range</th>
            <th className="py-2 font-medium">Decline</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {specs.map((spec) => {
            const value = metrics.markers.find((m) => m.marker === spec.marker)?.value;
            const deviation = deviations.get(spec.marker);
            const test = deviation?.test;
            const decline = DECLINE[spec.decline_direction];
            const Arrow = decline.icon;
            return (
              <tr key={spec.marker} className={test?.significant ? "bg-terra-50/60" : ""}>
                <td className="py-2 pr-3 text-slate-800">
                  {spec.label}
                  {!spec.in_change_index && (
                    <span className="ml-1.5 text-xs text-slate-400">context</span>
                  )}
                </td>
                <td className="py-2 pr-3 text-right">{formatNumber(value, 3)}</td>
                <td className="py-2 pr-3 text-right text-slate-600">
                  {deviation
                    ? `${formatNumber(deviation.baseline_mean, 3)} ± ${formatNumber(deviation.baseline_sd, 3)}`
                    : "—"}
                </td>
                <td className="py-2 pr-3 text-right text-slate-600">
                  {test ? `${formatNumber(test.t, 2)} (df ${test.df})` : "—"}
                </td>
                <td className="py-2 pr-3">
                  {test ? (
                    test.significant ? (
                      <span className="font-medium text-terra-700">Yes</span>
                    ) : (
                      <span className="text-slate-600">No</span>
                    )
                  ) : (
                    <span className="text-slate-400">Not tested</span>
                  )}
                </td>
                <td className="py-2 text-slate-500">
                  <Arrow aria-label={decline.text} className="size-4" />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-slate-500">
        One-sided Crawford–Howell test against the personal baseline, α = 0.05.
      </p>
    </div>
  );
}

export function QualityPanel({ quality }: { quality: QualityReport | null }) {
  if (!quality) return <p className="text-sm text-slate-500">Not assessed yet.</p>;
  const confidence =
    quality.mean_logprob === null || quality.mean_logprob === undefined
      ? "—"
      : `${Math.round(Math.exp(quality.mean_logprob) * 100)} %`;
  return (
    <div className="space-y-3 text-sm">
      <p className="font-medium text-slate-800">{QUALITY_LABELS[quality.status]}</p>
      {quality.reasons.length > 0 && (
        <ul className="list-disc space-y-1 pl-5 text-slate-600">
          {quality.reasons.map((reason) => (
            <li key={reason}>{QUALITY_REASON_TEXT[reason] ?? reason}</li>
          ))}
        </ul>
      )}
      <dl className="tabular grid grid-cols-2 gap-x-4 gap-y-1.5 text-slate-600">
        <dt>Words from the person</dt>
        <dd className="text-right text-slate-800">{quality.target_word_count}</dd>
        <dt>Speaking time</dt>
        <dd className="text-right text-slate-800">
          {formatDuration(quality.target_speaking_time_s)}
        </dd>
        <dt>Share of the speech</dt>
        <dd className="text-right text-slate-800">
          {Math.round(quality.target_speech_share * 100)} %
        </dd>
        <dt>Transcription confidence</dt>
        <dd className="text-right text-slate-800">{confidence}</dd>
      </dl>
    </div>
  );
}

/** Side by side values of two sessions, for the comparison view. */
export function CompareMarkers({
  current,
  reference,
  specs,
}: {
  current: SessionMetrics | null;
  reference: SessionMetrics | null;
  specs: readonly MarkerSpec[];
}) {
  const value = (metrics: SessionMetrics | null, marker: string) =>
    metrics?.markers.find((m) => m.marker === marker)?.value;
  return (
    <table className="tabular w-full text-left text-sm">
      <thead className="text-xs text-slate-500">
        <tr>
          <th className="py-2 pr-3 font-medium">Marker</th>
          <th className="py-2 pr-3 text-right font-medium">This session</th>
          <th className="py-2 pr-3 text-right font-medium">Reference</th>
          <th className="py-2 font-medium">Decline</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-100">
        {specs.map((spec) => {
          const decline = DECLINE[spec.decline_direction];
          const Arrow = decline.icon;
          return (
            <tr key={spec.marker}>
              <td className="py-1.5 pr-3 text-slate-800">{spec.label}</td>
              <td className="py-1.5 pr-3 text-right">{formatNumber(value(current, spec.marker), 3)}</td>
              <td className="py-1.5 pr-3 text-right text-slate-600">
                {formatNumber(value(reference, spec.marker), 3)}
              </td>
              <td className="py-1.5 text-slate-500">
                <Arrow aria-label={decline.text} className="size-4" />
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
