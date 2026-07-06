import { request } from "./http";

export function recordInterruption(sessionId: number, startedAt: string, endedAt: string, details: Record<string, unknown> = {}) {
  return request<Record<string, unknown>>(`/recovery/sessions/${sessionId}/interruptions`, {
    method: "POST",
    body: JSON.stringify({ started_at: startedAt, ended_at: endedAt, details })
  });
}

export function applyRecoveryAction(sessionId: number, eventId: number, action: "extend_questions" | "reopen_sign_in") {
  return request<Record<string, unknown>>(`/recovery/sessions/${sessionId}/actions`, {
    method: "POST",
    body: JSON.stringify({ event_id: eventId, action })
  });
}

export function recordCachedReplay(sessionId: number, payload: Record<string, unknown>) {
  return request<Record<string, unknown>>(`/recovery/sessions/${sessionId}/cached-replays`, {
    method: "POST",
    body: JSON.stringify({ payload })
  });
}

export function fetchRecoveryEvents(sessionId: number) {
  return request<Array<Record<string, unknown>>>(`/recovery/sessions/${sessionId}/events`);
}
