const STORAGE_KEY = "teaching_assist_student_session";

export interface StoredStudentSession {
  sessionId: number;
  token: string;
}

export function readStudentSession(): StoredStudentSession | null {
  try {
    const value = JSON.parse(sessionStorage.getItem(STORAGE_KEY) ?? "null") as Partial<StoredStudentSession> | null;
    return value && Number.isInteger(value.sessionId) && value.sessionId! > 0 && typeof value.token === "string" && value.token
      ? { sessionId: value.sessionId!, token: value.token }
      : null;
  } catch {
    return null;
  }
}

export function saveStudentSession(value: StoredStudentSession): void {
  try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value)); } catch { /* Storage may be disabled. */ }
}

export function clearStudentSession(): void {
  try { sessionStorage.removeItem(STORAGE_KEY); } catch { /* Storage may be disabled. */ }
}
