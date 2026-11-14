// Charts of the person page (docs/specs/clinician-ui.md, screen 2, items 3 to 5).
// Marks follow the dataviz rules: 2px lines, >= 8px markers with a surface ring,
// hairline solid grid, a baseline wash at ~10%, a crosshair tooltip, a table view.
import { Info } from "lucide-react";
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type {
  MarkerId,
  MarkerSpec,
  QualityStatus,
  TrajectoryPoint,
  Uncertainty,
} from "../api/types";
import { MIN_SIGNIFICANT_MARKERS } from "../api/types";
import { formatChange, formatDate, formatNumber, formatShortDate, formatStudy, plural } from "../lib/format";
import { DECLINE } from "../lib/decline";
import { LEVELS, QUALITY_LABELS } from "../lib/levels";

const INK = {
  line: "#475569",
  grid: "#e8eaed",
  axis: "#64748b",
  muted: "#94a3b8",
  surface: "#ffffff",
  sage: "#5e9384",
  terra: "#b9522c",
};

const AXIS_TICK = { fill: INK.axis, fontSize: 12 };

// --- Change from baseline ---------------------------------------------------

interface ChangeRow {
  time: number;
  sessionId: string;
  value: number;
  significant: number;
  tested: number;
  quality: QualityStatus;
  level: string;
}

function changeRows(points: readonly TrajectoryPoint[]): ChangeRow[] {
  return points.flatMap((point) => {
    const index = point.comparison?.change_index;
    if (!point.comparison || !index) return [];
    return [
      {
        time: Date.parse(point.recorded_at),
        sessionId: point.session_id,
        value: index.value,
        significant: index.significant_markers.length,
        tested: index.tested_markers.length,
        quality: point.quality_status,
        level: LEVELS[point.comparison.orientation.level].label,
      },
    ];
  });
}

function timeDomain(points: readonly TrajectoryPoint[]): [number, number] {
  const times = points.map((p) => Date.parse(p.recorded_at));
  const pad = 4 * 24 * 3600 * 1000;
  return [Math.min(...times) - pad, Math.max(...times) + pad];
}

interface DotProps {
  cx?: number;
  cy?: number;
  payload?: ChangeRow;
}

function ChangeDot({ cx, cy, payload, onOpen }: DotProps & { onOpen: (id: string) => void }) {
  if (cx === undefined || cy === undefined || !payload) return null;
  const deviation = payload.significant >= MIN_SIGNIFICANT_MARKERS;
  const partial = payload.quality === "partial";
  const color = deviation ? INK.terra : INK.line;
  return (
    <g
      onClick={() => onOpen(payload.sessionId)}
      style={{ cursor: "pointer" }}
      aria-label={`Session of ${formatDate(new Date(payload.time).toISOString())}`}
    >
      {/* Hit area larger than the mark. */}
      <circle cx={cx} cy={cy} r={12} fill="transparent" />
      <circle
        cx={cx}
        cy={cy}
        r={deviation ? 6 : 4.5}
        fill={partial ? INK.surface : color}
        stroke={partial ? color : INK.surface}
        strokeWidth={2}
      />
      {deviation && (
        <text
          x={cx}
          y={cy - 13}
          textAnchor="middle"
          fontSize={11}
          fontWeight={600}
          fill="#334155"
        >
          {plural(payload.significant, "marker")}
        </text>
      )}
    </g>
  );
}

function TooltipShell({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-lg">
      {children}
    </div>
  );
}

interface TooltipProps<T> {
  active?: boolean;
  payload?: readonly { payload?: T }[];
}

function ChangeTooltip({ active, payload }: TooltipProps<ChangeRow | RejectedRow>) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
  if ("rejected" in row) {
    return (
      <TooltipShell>
        <p className="font-semibold text-slate-800">Rejected session</p>
        <p className="text-slate-500">{formatDate(new Date(row.time).toISOString())}</p>
      </TooltipShell>
    );
  }
  return (
    <TooltipShell>
      <p className="text-sm font-semibold text-slate-900">{formatChange(row.value)}</p>
      <p className="text-slate-500">{formatDate(new Date(row.time).toISOString())}</p>
      <p className="mt-1 text-slate-700">
        {row.significant} of {row.tested} markers beyond the usual range
      </p>
      <p className="text-slate-500">
        {row.level} · {QUALITY_LABELS[row.quality]}
      </p>
    </TooltipShell>
  );
}

interface RejectedRow {
  time: number;
  y: number;
  rejected: true;
}

export function ChangeFromBaselineChart({
  points,
  uncertainty,
}: {
  points: readonly TrajectoryPoint[];
  uncertainty: Uncertainty | null;
}) {
  const navigate = useNavigate();
  const rows = changeRows(points);
  if (rows.length === 0) {
    return (
      <p className="py-8 text-sm text-slate-500">
        The curve appears once the personal baseline has 3 usable sessions.
      </p>
    );
  }
  const range = uncertainty?.baseline_change_index_range ?? null;
  const values = [...rows.map((r) => r.value), ...(range ?? []), 0];
  const top = Math.ceil(Math.max(...values) + 0.6);
  const bottom = Math.floor(Math.min(...values) - 0.6);
  // Whole numbers of standard deviations, in steps of 1 or 2.
  const step = top - bottom > 8 ? 2 : 1;
  const ticks: number[] = [];
  for (let tick = Math.ceil(bottom / step) * step; tick <= top; tick += step) ticks.push(tick);
  const rejected: RejectedRow[] = points
    .filter((p) => p.quality_status === "rejected")
    .map((p) => ({ time: Date.parse(p.recorded_at), y: bottom, rejected: true }));

  return (
    <div>
      <div className="h-[280px]" role="img" aria-label="Change from baseline over time">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 24, right: 16, bottom: 4, left: 0 }}>
            <CartesianGrid stroke={INK.grid} vertical={false} />
            {range && (
              <ReferenceArea
                y1={range[0]}
                y2={range[1]}
                fill={INK.sage}
                fillOpacity={0.12}
                stroke="none"
                ifOverflow="extendDomain"
              />
            )}
            <ReferenceLine y={0} stroke={INK.sage} strokeWidth={1} />
            <XAxis
              dataKey="time"
              type="number"
              scale="time"
              domain={timeDomain(points)}
              tickFormatter={formatShortDate}
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={{ stroke: INK.grid }}
              minTickGap={24}
            />
            <YAxis
              domain={[bottom, top]}
              ticks={ticks}
              tickFormatter={(v: number) => (v > 0 ? `+${v}` : String(v))}
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={false}
              width={40}
            />
            <Tooltip
              content={<ChangeTooltip />}
              cursor={{ stroke: INK.muted, strokeWidth: 1 }}
              isAnimationActive={false}
            />
            <Line
              dataKey="value"
              stroke={INK.line}
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              isAnimationActive={false}
              dot={(props: DotProps) => (
                <ChangeDot
                  key={props.payload?.sessionId}
                  {...props}
                  onOpen={(id) => navigate(`/sessions/${id}`)}
                />
              )}
              activeDot={false}
            />
            {rejected.length > 0 && (
              <Scatter
                data={rejected}
                dataKey="y"
                isAnimationActive={false}
                shape={(props: { cx?: number; cy?: number }) => (
                  <g>
                    <path
                      d={`M${(props.cx ?? 0) - 4},${(props.cy ?? 0) - 4} l8,8 m0,-8 l-8,8`}
                      stroke={INK.axis}
                      strokeWidth={2}
                      strokeLinecap="round"
                    />
                  </g>
                )}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <ChangeLegend hasRange={range !== null} hasRejected={rejected.length > 0} />
    </div>
  );
}

function ChangeLegend({ hasRange, hasRejected }: { hasRange: boolean; hasRejected: boolean }) {
  return (
    <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-600">
      {hasRange && (
        <li className="flex items-center gap-1.5">
          <span className="h-3 w-5 rounded-sm bg-sage-500/15" /> Range of the baseline sessions
        </li>
      )}
      <li className="flex items-center gap-1.5">
        <span className="size-2.5 rounded-full bg-slate-600" /> Usable session
      </li>
      <li className="flex items-center gap-1.5">
        <span className="size-2.5 rounded-full border-2 border-slate-600 bg-white" /> Partial
        session
      </li>
      <li className="flex items-center gap-1.5">
        <span className="size-3 rounded-full bg-terra-500" /> Session beyond the usual range (≥ 2
        markers)
      </li>
      {hasRejected && (
        <li className="flex items-center gap-1.5">
          <span className="font-semibold text-slate-500">×</span> Rejected session
        </li>
      )}
    </ul>
  );
}

export function ChangeTable({ points }: { points: readonly TrajectoryPoint[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="tabular w-full text-left text-sm">
        <thead className="text-xs text-slate-500">
          <tr>
            <th className="py-1.5 pr-4 font-medium">Session</th>
            <th className="py-1.5 pr-4 font-medium">Change from baseline</th>
            <th className="py-1.5 pr-4 font-medium">Markers beyond range</th>
            <th className="py-1.5 pr-4 font-medium">Quality</th>
            <th className="py-1.5 font-medium">Level</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {points.map((point) => {
            const index = point.comparison?.change_index;
            return (
              <tr key={point.session_id}>
                <td className="py-1.5 pr-4">{formatDate(point.recorded_at)}</td>
                <td className="py-1.5 pr-4">{index ? formatChange(index.value) : "—"}</td>
                <td className="py-1.5 pr-4">
                  {index ? `${index.significant_markers.length} of ${index.tested_markers.length}` : "—"}
                </td>
                <td className="py-1.5 pr-4">{QUALITY_LABELS[point.quality_status]}</td>
                <td className="py-1.5">
                  {point.comparison ? LEVELS[point.comparison.orientation.level].label : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// --- Small multiples --------------------------------------------------------

interface SmallRow {
  time: number;
  value: number;
  significant: boolean;
}

function SmallTooltip({
  active,
  payload,
  format,
}: TooltipProps<SmallRow> & { format: (value: number) => string }) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
  return (
    <TooltipShell>
      <p className="text-sm font-semibold text-slate-900">{format(row.value)}</p>
      <p className="text-slate-500">{formatDate(new Date(row.time).toISOString())}</p>
      {row.significant && <p className="mt-1 text-slate-700">Beyond the usual range</p>}
    </TooltipShell>
  );
}

function SmallChart({
  rows,
  domain,
  band,
  reference,
  format,
  label,
}: {
  rows: SmallRow[];
  domain: [number, number];
  band: [number, number] | null;
  reference: number | null;
  format: (value: number) => string;
  label: string;
}) {
  return (
    <div className="h-[110px]" role="img" aria-label={label}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={INK.grid} vertical={false} />
          {band && (
            <ReferenceArea
              y1={band[0]}
              y2={band[1]}
              fill={INK.sage}
              fillOpacity={0.12}
              stroke="none"
              ifOverflow="extendDomain"
            />
          )}
          {reference !== null && <ReferenceLine y={reference} stroke={INK.sage} />}
          <XAxis dataKey="time" type="number" scale="time" domain={domain} hide />
          <YAxis
            tick={{ ...AXIS_TICK, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={44}
            tickCount={3}
            domain={["auto", "auto"]}
            tickFormatter={(v: number) => formatNumber(v, 2)}
          />
          <Tooltip
            content={<SmallTooltip format={format} />}
            cursor={{ stroke: INK.muted, strokeWidth: 1 }}
            isAnimationActive={false}
          />
          <Line
            dataKey="value"
            stroke={INK.line}
            strokeWidth={2}
            isAnimationActive={false}
            dot={(props: { cx?: number; cy?: number; payload?: SmallRow; index?: number }) => {
              const { cx, cy, payload } = props;
              if (cx === undefined || cy === undefined || !payload) return <g key={props.index} />;
              return (
                <circle
                  key={payload.time}
                  cx={cx}
                  cy={cy}
                  r={payload.significant ? 4.5 : 3}
                  fill={payload.significant ? INK.terra : INK.line}
                  stroke={INK.surface}
                  strokeWidth={2}
                />
              );
            }}
            activeDot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export function FamilyCharts({ points }: { points: readonly TrajectoryPoint[] }) {
  const domain = timeDomain(points);
  const families = [
    { family: "semantic", title: "Semantic", hint: "pronouns, nouns, word frequency, word length" },
    { family: "fluency", title: "Fluency", hint: "hesitations and repetitions, speech rate" },
  ] as const;
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {families.map(({ family, title, hint }) => {
        const rows = points.flatMap((point) => {
          const score = point.comparison?.family_scores.find((f) => f.family === family);
          return score
            ? [{ time: Date.parse(point.recorded_at), value: score.value, significant: false }]
            : [];
        });
        return (
          <div key={family}>
            <p className="text-sm font-medium text-slate-700">{title}</p>
            <p className="mb-1 text-xs text-slate-500">{hint}</p>
            {rows.length ? (
              <SmallChart
                rows={rows}
                domain={domain}
                band={null}
                reference={0}
                format={formatChange}
                label={`${title} sub-score over time`}
              />
            ) : (
              <p className="py-6 text-xs text-slate-500">Available once the baseline exists.</p>
            )}
          </div>
        );
      })}
    </div>
  );
}

function markerRows(points: readonly TrajectoryPoint[], marker: MarkerId): SmallRow[] {
  return points.flatMap((point) => {
    const value = point.metrics?.markers.find((m) => m.marker === marker)?.value;
    if (value === null || value === undefined) return [];
    const test = point.comparison?.markers.find((m) => m.marker === marker)?.test;
    return [{ time: Date.parse(point.recorded_at), value, significant: Boolean(test?.significant) }];
  });
}

function MarkerInfo({ spec }: { spec: MarkerSpec }) {
  return (
    <span className="group relative inline-flex">
      <button
        type="button"
        className="rounded text-slate-400 hover:text-slate-700"
        aria-label={`About ${spec.label}`}
      >
        <Info aria-hidden className="size-3.5" />
      </button>
      <span
        role="tooltip"
        className="pointer-events-none invisible absolute top-5 left-1/2 z-20 w-64 -translate-x-1/2 rounded-lg border border-slate-200 bg-white p-3 text-xs leading-relaxed text-slate-700 opacity-0 shadow-lg transition group-focus-within:visible group-focus-within:opacity-100 group-hover:visible group-hover:opacity-100"
      >
        {spec.definition}
        <span className="mt-1 block text-slate-500">
          Source: {spec.sources.map(formatStudy).join(", ")}
        </span>
      </span>
    </span>
  );
}

export function MarkerCharts({
  points,
  specs,
}: {
  points: readonly TrajectoryPoint[];
  specs: readonly MarkerSpec[];
}) {
  const domain = timeDomain(points);
  const baseline = [...points].reverse().find((p) => p.comparison?.baseline)?.comparison?.baseline;
  const groups = [
    { title: "In the change index", specs: specs.filter((s) => s.in_change_index) },
    { title: "Shown for context, not in the index", specs: specs.filter((s) => !s.in_change_index) },
  ];
  return (
    <div className="space-y-6">
      {groups.map((group) => (
        <div key={group.title}>
          <h3 className="mb-3 text-xs font-semibold tracking-wide text-slate-500 uppercase">
            {group.title}
          </h3>
          <div className="grid gap-x-6 gap-y-5 sm:grid-cols-2 lg:grid-cols-3">
            {group.specs.map((spec) => {
              const reference = baseline?.markers.find((m) => m.marker === spec.marker);
              const band: [number, number] | null = reference
                ? [reference.mean - reference.sd, reference.mean + reference.sd]
                : null;
              const decline = DECLINE[spec.decline_direction];
              const Arrow = decline.icon;
              return (
                <div key={spec.marker}>
                  <div className="flex items-center gap-1.5">
                    <p className="text-sm font-medium text-slate-700">{spec.label}</p>
                    <MarkerInfo spec={spec} />
                  </div>
                  <p className="mb-1 flex items-center gap-1 text-xs text-slate-500">
                    <Arrow aria-hidden className="size-3" />
                    {decline.text}
                  </p>
                  <SmallChart
                    rows={markerRows(points, spec.marker)}
                    domain={domain}
                    band={band}
                    reference={reference?.mean ?? null}
                    format={(v) => formatNumber(v, 3)}
                    label={`${spec.label} over time`}
                  />
                </div>
              );
            })}
          </div>
        </div>
      ))}
      <p className="text-xs text-slate-500">
        Shaded band: baseline mean ± 1 standard deviation. A point is marked when the
        session-level test finds the marker beyond the person's usual range.
      </p>
    </div>
  );
}
