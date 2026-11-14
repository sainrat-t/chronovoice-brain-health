// Calls to the ChronoVoice API (docs/specs/api.md). Same origin: the Vite dev server
// proxies /api to the backend, and in production FastAPI serves this app.
import type {
  ClinicalSummaryReport,
  Person,
  PersonCreate,
  PersonDetail,
  PersonSummary,
  Prompt,
  SessionAccepted,
  SessionDetail,
  SessionStatusView,
  SessionUpload,
} from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, detail: unknown) {
    super(describe(status, detail));
    this.status = status;
    this.detail = detail;
  }
}

function describe(status: number, detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item: unknown) =>
        item && typeof item === "object" && "msg" in item ? String(item.msg) : null,
      )
      .filter(Boolean);
    if (messages.length) return messages.join("; ");
  }
  return status === 0 ? "The server could not be reached" : `Request failed (${status})`;
}

async function request<T>(path: string, init?: RequestInit & { json?: unknown }): Promise<T> {
  const { json, ...rest } = init ?? {};
  let response: Response;
  try {
    response = await fetch(path, {
      ...rest,
      headers: json === undefined ? rest.headers : { "Content-Type": "application/json" },
      body: json === undefined ? rest.body : JSON.stringify(json),
    });
  } catch {
    throw new ApiError(0, null);
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body && typeof body === "object" && "detail" in body ? body.detail : null;
    throw new ApiError(response.status, detail);
  }
  return body as T;
}

const id = encodeURIComponent;

export const api = {
  people: () => request<PersonSummary[]>("/api/people"),
  person: (personId: string) => request<PersonDetail>(`/api/people/${id(personId)}`),
  createPerson: (body: PersonCreate) =>
    request<Person>("/api/people", { method: "POST", json: body }),
  session: (sessionId: string) => request<SessionDetail>(`/api/sessions/${id(sessionId)}`),
  sessionStatus: (sessionId: string) =>
    request<SessionStatusView>(`/api/sessions/${id(sessionId)}/status`),
  retrySession: (sessionId: string) =>
    request<SessionAccepted>(`/api/sessions/${id(sessionId)}/retry`, { method: "POST" }),
  reviewSummary: (personId: string, reviewedBy: string) =>
    request<ClinicalSummaryReport>(`/api/people/${id(personId)}/summary/review`, {
      method: "POST",
      json: { reviewed_by: reviewedBy },
    }),
  prompt: (personId: string, exclude: readonly string[]) => {
    const params = new URLSearchParams({ person_id: personId });
    exclude.forEach((promptId) => params.append("exclude", promptId));
    return request<Prompt>(`/api/prompts?${params.toString()}`);
  },
};

/**
 * Send a recording. XMLHttpRequest rather than fetch, for the upload progress.
 * The audio stays with the caller, so a failed send can be retried without loss.
 */
export function uploadSession(
  personId: string,
  audio: Blob,
  filename: string,
  metadata: SessionUpload,
  onProgress: (fraction: number) => void,
): Promise<SessionAccepted> {
  const form = new FormData();
  form.append("audio", audio, filename);
  form.append("metadata", JSON.stringify(metadata));
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/api/people/${id(personId)}/sessions`);
    xhr.responseType = "json";
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded / event.total);
    };
    xhr.onload = () => {
      const body: unknown = xhr.response;
      if (xhr.status === 202) {
        resolve(body as SessionAccepted);
      } else {
        const detail = body && typeof body === "object" && "detail" in body ? body.detail : null;
        reject(new ApiError(xhr.status, detail));
      }
    };
    xhr.onerror = () => reject(new ApiError(0, null));
    xhr.send(form);
  });
}
