// Microphone recording in the browser (docs/specs/clinician-ui.md, section 3):
// MediaRecorder, opus in WebM where supported (Chrome, Firefox), else MP4 (Safari).
import { useCallback, useEffect, useRef, useState } from "react";

export const MAX_SECONDS = 15 * 60;
/** Below this, the session will be "partial" (docs/specs/pipeline.md, step 0). */
export const PARTIAL_BELOW_SECONDS = 2 * 60;
export const TARGET_SECONDS = 5 * 60;
const SILENCE_CHECK_SECONDS = 10;
const SILENCE_LEVEL = 0.02;

export type RecorderState =
  | { phase: "idle" }
  | { phase: "requesting" }
  | { phase: "denied"; message: string }
  | { phase: "recording" }
  | { phase: "recorded"; audio: Blob; filename: string; seconds: number };

function pickMimeType(): string | undefined {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type));
}

export function useRecorder() {
  const [state, setState] = useState<RecorderState>({ phase: "idle" });
  const [seconds, setSeconds] = useState(0);
  const [level, setLevel] = useState(0);
  const [silent, setSilent] = useState(false);

  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const audioContext = useRef<AudioContext | null>(null);
  const frame = useRef<number | null>(null);
  const timer = useRef<number | null>(null);
  const chunks = useRef<Blob[]>([]);
  const startedAt = useRef(0);
  const loudest = useRef(0);

  const release = useCallback(() => {
    if (frame.current !== null) cancelAnimationFrame(frame.current);
    if (timer.current !== null) window.clearInterval(timer.current);
    frame.current = null;
    timer.current = null;
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
    void audioContext.current?.close();
    audioContext.current = null;
    setLevel(0);
  }, []);

  const stop = useCallback(() => {
    if (recorder.current && recorder.current.state !== "inactive") recorder.current.stop();
  }, []);

  const start = useCallback(async () => {
    setState({ phase: "requesting" });
    setSilent(false);
    let media: MediaStream;
    try {
      // Noise suppression could remove the hesitations the fluency markers count.
      media = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: false },
      });
    } catch (reason) {
      const name = reason instanceof DOMException ? reason.name : "";
      setState({
        phase: "denied",
        message:
          name === "NotAllowedError"
            ? "Access to the microphone was refused. Allow it in the browser, or upload an audio file instead."
            : "No microphone could be used. Check it is connected, or upload an audio file instead.",
      });
      return;
    }
    stream.current = media;
    const mimeType = pickMimeType();
    const mediaRecorder = new MediaRecorder(media, mimeType ? { mimeType } : undefined);
    recorder.current = mediaRecorder;
    chunks.current = [];
    loudest.current = 0;
    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunks.current.push(event.data);
    };
    mediaRecorder.onstop = () => {
      const type = mediaRecorder.mimeType || mimeType || "audio/webm";
      const audio = new Blob(chunks.current, { type });
      const elapsed = (performance.now() - startedAt.current) / 1000;
      release();
      setState({
        phase: "recorded",
        audio,
        filename: type.includes("mp4") ? "recording.m4a" : "recording.webm",
        seconds: elapsed,
      });
    };

    // Level meter, and a warning when nothing is heard.
    const context = new AudioContext();
    audioContext.current = context;
    const analyser = context.createAnalyser();
    analyser.fftSize = 1024;
    context.createMediaStreamSource(media).connect(analyser);
    const samples = new Float32Array(analyser.fftSize);
    const measure = () => {
      analyser.getFloatTimeDomainData(samples);
      let sum = 0;
      for (const sample of samples) sum += sample * sample;
      const rms = Math.sqrt(sum / samples.length);
      loudest.current = Math.max(loudest.current, rms);
      setLevel(Math.min(1, rms * 6));
      frame.current = requestAnimationFrame(measure);
    };
    measure();

    startedAt.current = performance.now();
    setSeconds(0);
    timer.current = window.setInterval(() => {
      const elapsed = (performance.now() - startedAt.current) / 1000;
      setSeconds(elapsed);
      if (elapsed >= SILENCE_CHECK_SECONDS && loudest.current < SILENCE_LEVEL) setSilent(true);
      if (elapsed >= MAX_SECONDS) stop();
    }, 250);
    mediaRecorder.start(1000);
    setState({ phase: "recording" });
  }, [release, stop]);

  const reset = useCallback(() => {
    release();
    setSeconds(0);
    setSilent(false);
    setState({ phase: "idle" });
  }, [release]);

  useEffect(() => () => {
    if (recorder.current && recorder.current.state !== "inactive") {
      recorder.current.onstop = null;
      recorder.current.stop();
    }
    release();
  }, [release]);

  return { state, seconds, level, silent, start, stop, reset };
}
