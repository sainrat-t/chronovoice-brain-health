// Screen 4: a new session in five steps on one page: consent, context, opening
// question, recording (or an audio file), then the processing.
import {
  ArrowLeft,
  Check,
  CircleAlert,
  LoaderCircle,
  Mic,
  RefreshCw,
  Square,
  Upload,
} from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError, api, uploadSession } from "../api/client";
import type { Prompt, RecordingContext, SessionStatusView } from "../api/types";
import { Card, ErrorNote, Loading } from "../components/ui";
import { buttonStyles } from "../lib/styles";
import { formatClock } from "../lib/format";
import { QUALITY_REASON_TEXT } from "../lib/levels";
import { useApi } from "../lib/useApi";
import { MAX_SECONDS, PARTIAL_BELOW_SECONDS, TARGET_SECONDS, useRecorder } from "../lib/useRecorder";

type Choice<T> = { value: T; label: string };

function Segmented<T extends string | boolean>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: Choice<T>[];
  value: T | null | undefined;
  onChange: (value: T | null) => void;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 py-2">
      <span className="text-sm text-slate-700">{label}</span>
      <div className="inline-flex rounded-lg border border-slate-300 bg-white p-0.5" role="group">
        {options.map((option) => {
          const selected = value === option.value;
          return (
            <button
              key={String(option.value)}
              type="button"
              aria-pressed={selected}
              onClick={() => onChange(selected ? null : option.value)}
              className={`rounded-md px-3 py-1 text-sm ${
                selected ? "bg-slate-800 text-white" : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

const YES_NO: Choice<boolean>[] = [
  { value: true, label: "Yes" },
  { value: false, label: "No" },
];

function Step({
  number,
  title,
  done,
  children,
}: {
  number: number;
  title: string;
  done: boolean;
  children: ReactNode;
}) {
  return (
    <Card>
      <div className="flex gap-4">
        <span
          className={`flex size-7 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${
            done ? "bg-sage-100 text-sage-800" : "bg-slate-100 text-slate-600"
          }`}
        >
          {done ? <Check aria-hidden className="size-4" /> : number}
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="mb-3 text-base font-semibold text-slate-800">{title}</h2>
          {children}
        </div>
      </div>
    </Card>
  );
}

const PIPELINE: { status: SessionStatusView["status"]; label: string }[] = [
  { status: "transcribing", label: "Transcribing" },
  { status: "analysing", label: "Analysing" },
  { status: "summarising", label: "Writing summary" },
  { status: "done", label: "Done" },
];

function Processing({ sessionId }: { sessionId: string }) {
  const navigate = useNavigate();
  const [status, setStatus] = useState<SessionStatusView | null>(null);
  const [reasons, setReasons] = useState<string[]>([]);

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const current = await api.sessionStatus(sessionId);
        if (!active) return;
        setStatus(current);
        if (current.status === "done") navigate(`/sessions/${sessionId}`);
        if (current.status === "rejected") {
          const detail = await api.session(sessionId);
          if (active) setReasons(detail.quality?.reasons ?? []);
        }
      } catch {
        // A missed poll is retried at the next tick.
      }
    };
    void poll();
    const timer = window.setInterval(poll, 2000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [sessionId, navigate]);

  const reached = PIPELINE.findIndex((step) => step.status === status?.status);
  if (status?.status === "rejected") {
    return (
      <div className="space-y-2 text-sm">
        <p className="font-medium text-terra-800">
          The session was set aside by the quality check:
        </p>
        <ul className="list-disc pl-5 text-slate-700">
          {reasons.map((reason) => (
            <li key={reason}>{QUALITY_REASON_TEXT[reason] ?? reason}</li>
          ))}
        </ul>
        <Link className="underline" to={`/sessions/${sessionId}`}>
          See the session
        </Link>
      </div>
    );
  }
  if (status?.status === "failed") {
    return (
      <div className="space-y-2 text-sm">
        <p className="text-terra-800">The session could not be processed: {status.error}</p>
        <Link className={buttonStyles.secondary} to={`/sessions/${sessionId}`}>
          Open the session to try again
        </Link>
      </div>
    );
  }
  return (
    <ol className="flex flex-wrap items-center gap-3 text-sm" aria-live="polite">
      {PIPELINE.map((step, index) => {
        const done = index < reached;
        const current = index === reached || (reached === -1 && index === 0);
        return (
          <li key={step.status} className="flex items-center gap-2">
            <span
              className={`flex size-6 items-center justify-center rounded-full ${
                done
                  ? "bg-sage-100 text-sage-800"
                  : current
                    ? "bg-slate-800 text-white"
                    : "bg-slate-100 text-slate-400"
              }`}
            >
              {done ? (
                <Check aria-hidden className="size-3.5" />
              ) : current ? (
                <LoaderCircle aria-hidden className="size-3.5 animate-spin" />
              ) : (
                index + 1
              )}
            </span>
            <span className={current ? "font-medium text-slate-900" : "text-slate-600"}>
              {step.label}
            </span>
            {index < PIPELINE.length - 1 && <span className="text-slate-300">→</span>}
          </li>
        );
      })}
    </ol>
  );
}

export function NewSession() {
  const { personId = "" } = useParams();
  const person = useApi(() => api.person(personId), [personId]);
  const recorder = useRecorder();
  const fileInput = useRef<HTMLInputElement>(null);

  const [consent, setConsent] = useState(false);
  const [context, setContext] = useState<RecordingContext>({});
  const [offered, setOffered] = useState<string[]>([]);
  const [prompt, setPrompt] = useState<Prompt | null>(null);
  const [promptError, setPromptError] = useState<Error | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [sendError, setSendError] = useState<Error | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  async function drawPrompt(exclude: string[]) {
    setPromptError(null);
    try {
      const next = await api.prompt(personId, exclude);
      setPrompt(next);
      setOffered((list) => (list.includes(next.prompt_id) ? list : [...list, next.prompt_id]));
    } catch (reason) {
      setPromptError(reason instanceof Error ? reason : new Error(String(reason)));
    }
  }

  // A first theme when the page opens.
  useEffect(() => {
    let active = true;
    api.prompt(personId, []).then(
      (first) => {
        if (!active) return;
        setPrompt(first);
        setOffered([first.prompt_id]);
      },
      (reason: unknown) => {
        if (active) setPromptError(reason instanceof Error ? reason : new Error(String(reason)));
      },
    );
    return () => {
      active = false;
    };
  }, [personId]);

  const recorded = recorder.state.phase === "recorded" ? recorder.state : null;
  const audio = file ?? recorded?.audio ?? null;
  const filename = file?.name ?? recorded?.filename ?? "recording.webm";

  async function send() {
    if (!audio || !consent) return;
    setSendError(null);
    setProgress(0);
    try {
      const accepted = await uploadSession(
        personId,
        audio,
        filename,
        { consent: true, context, prompt_id: prompt?.prompt_id ?? null },
        setProgress,
      );
      setSessionId(accepted.session_id);
    } catch (reason) {
      // The recording is kept: the clinician can send it again.
      setSendError(
        reason instanceof ApiError && reason.status === 0
          ? new Error("The recording could not be sent (network). It is kept: try again.")
          : reason instanceof Error
            ? reason
            : new Error(String(reason)),
      );
    } finally {
      setProgress(null);
    }
  }

  if (person.error) return <ErrorNote error={person.error} onRetry={person.reload} />;
  if (!person.data) return <Loading />;
  const recording = recorder.state.phase === "recording";
  const locked = sessionId !== null || progress !== null;

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <Link to={`/people/${personId}`} className={buttonStyles.quiet}>
        <ArrowLeft aria-hidden className="size-4" /> {person.data.person.display_name}
      </Link>
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">New session</h1>

      <Step number={1} title="Consent" done={consent}>
        <label className="flex items-start gap-3 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={consent}
            disabled={locked}
            onChange={(event) => setConsent(event.target.checked)}
            className="mt-0.5 size-4 accent-slate-800"
          />
          <span>
            <span className="font-medium text-slate-900">Consent obtained for this recording.</span>{" "}
            The audio is transcribed, then deleted; only the transcript and the measures are
            kept, to follow how this person's speech changes over time.
          </span>
        </label>
      </Step>

      <Step number={2} title="Context of the day" done={Object.keys(context).length > 0}>
        <div className="divide-y divide-slate-100">
          <Segmented
            label="Sleep last night"
            options={[
              { value: "good", label: "Good" },
              { value: "average", label: "Average" },
              { value: "poor", label: "Poor" },
            ]}
            value={context.sleep}
            onChange={(sleep) => setContext({ ...context, sleep })}
          />
          <Segmented
            label="Feeling tired"
            options={YES_NO}
            value={context.fatigue}
            onChange={(fatigue) => setContext({ ...context, fatigue })}
          />
          <Segmented
            label="Acute illness (cold, infection…)"
            options={YES_NO}
            value={context.acute_illness}
            onChange={(acute_illness) => setContext({ ...context, acute_illness })}
          />
          <Segmented
            label="New treatment since the last session"
            options={YES_NO}
            value={context.new_medication}
            onChange={(new_medication) => setContext({ ...context, new_medication })}
          />
          <Segmented
            label="Mood"
            options={[
              { value: "good", label: "Good" },
              { value: "neutral", label: "Neutral" },
              { value: "low", label: "Low" },
            ]}
            value={context.mood}
            onChange={(mood) => setContext({ ...context, mood })}
          />
        </div>
        <p className="mt-2 text-xs text-slate-500">
          A poor night or a cold can change how anyone speaks: a session with such a context
          cannot on its own lead to a review.
        </p>
      </Step>

      <Step number={3} title="Opening question" done={prompt !== null}>
        {promptError && <ErrorNote error={promptError} />}
        {prompt && (
          <div className="rounded-xl bg-sage-50 p-5 ring-1 ring-sage-200">
            <p className="text-xs font-semibold tracking-wide text-sage-800 uppercase">
              {prompt.theme}
            </p>
            <p className="mt-1 text-lg font-medium text-slate-900">“{prompt.question}”</p>
            <p className="mt-3 text-sm text-slate-600">
              Neutral follow-ups: {prompt.follow_ups.map((f) => `“${f}”`).join(" · ")}
            </p>
          </div>
        )}
        <button
          type="button"
          className={`${buttonStyles.quiet} mt-2`}
          disabled={locked || recording}
          onClick={() => drawPrompt(offered)}
        >
          <RefreshCw aria-hidden className="size-4" /> Another theme
        </button>
      </Step>

      <Step number={4} title="Recording" done={audio !== null}>
        {!consent && (
          <p className="mb-3 text-sm text-slate-500">Tick the consent box to start recording.</p>
        )}
        {recorder.state.phase === "denied" && (
          <p className="mb-3 flex items-start gap-2 text-sm text-terra-800">
            <CircleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
            {recorder.state.message}
          </p>
        )}
        {!file && (
          <div className="flex flex-wrap items-center gap-4">
            {recording ? (
              <button type="button" className={buttonStyles.primary} onClick={recorder.stop}>
                <Square aria-hidden className="size-4 fill-current" /> Stop
              </button>
            ) : (
              <button
                type="button"
                className={buttonStyles.primary}
                disabled={!consent || locked || recorder.state.phase === "requesting"}
                onClick={() => {
                  recorder.reset();
                  void recorder.start();
                }}
              >
                <Mic aria-hidden className="size-4" />
                {recorded ? "Record again" : "Start recording"}
              </button>
            )}
            {(recording || recorded) && (
              <div className="flex items-center gap-3">
                <span className="tabular text-2xl font-semibold text-slate-900">
                  {formatClock(recorded ? recorded.seconds : recorder.seconds)}
                </span>
                <span className="text-sm text-slate-500">target {formatClock(TARGET_SECONDS)}</span>
              </div>
            )}
            {recording && (
              <div className="h-2 w-40 overflow-hidden rounded-full bg-slate-100" aria-hidden>
                <div
                  className="h-full rounded-full bg-sage-500 transition-[width] duration-75"
                  style={{ width: `${Math.round(recorder.level * 100)}%` }}
                />
              </div>
            )}
          </div>
        )}
        {recording && recorder.seconds < PARTIAL_BELOW_SECONDS && (
          <p className="mt-3 text-sm text-slate-600">
            Under 2 minutes, the session will be marked partial: it is shown, but it does not
            change the orientation.
          </p>
        )}
        {recording && recorder.silent && (
          <p className="mt-3 flex items-center gap-2 text-sm text-terra-800">
            <CircleAlert aria-hidden className="size-4" /> No sound heard for 10 seconds: check
            the microphone.
          </p>
        )}
        {recording && (
          <p className="mt-2 text-xs text-slate-500">
            The recording stops by itself after {MAX_SECONDS / 60} minutes.
          </p>
        )}
        <div className="mt-4 border-t border-slate-100 pt-3 text-sm">
          <input
            ref={fileInput}
            type="file"
            accept="audio/*,video/mp4,video/webm"
            className="hidden"
            onChange={(event) => {
              const chosen = event.target.files?.[0] ?? null;
              setFile(chosen);
              if (chosen) recorder.reset();
            }}
          />
          {file ? (
            <p className="flex flex-wrap items-center gap-3 text-slate-700">
              <Upload aria-hidden className="size-4" /> {file.name}
              <button
                type="button"
                className="text-slate-500 underline"
                disabled={locked}
                onClick={() => setFile(null)}
              >
                Remove
              </button>
            </p>
          ) : (
            <button
              type="button"
              className="text-slate-600 underline underline-offset-2 hover:text-slate-900"
              disabled={locked || recording}
              onClick={() => fileInput.current?.click()}
            >
              Upload an audio file instead
            </button>
          )}
        </div>
      </Step>

      <Step number={5} title="Processing" done={false}>
        {sessionId ? (
          <Processing sessionId={sessionId} />
        ) : (
          <div className="space-y-3">
            <button
              type="button"
              className={buttonStyles.primary}
              disabled={!audio || !consent || progress !== null || recording}
              onClick={send}
            >
              {progress !== null ? (
                <>
                  <LoaderCircle aria-hidden className="size-4 animate-spin" /> Sending{" "}
                  {Math.round(progress * 100)} %
                </>
              ) : sendError ? (
                "Send again"
              ) : (
                "Send for analysis"
              )}
            </button>
            {sendError && <ErrorNote error={sendError} />}
            <p className="text-xs text-slate-500">
              Transcription, analysis and summary take about a minute.
            </p>
          </div>
        )}
      </Step>
    </div>
  );
}
