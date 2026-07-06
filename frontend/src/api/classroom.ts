import { ClassroomSession } from "./academic";
import { downloadFile, request } from "./http";

export interface SignInRecord {
  student_pk: number;
  student_number: string;
  student_name: string;
  class_name: string;
  record_id: number | null;
  status: "normal" | "late" | "absent" | null;
  sign_time: string | null;
  ip_address: string | null;
  user_agent: string | null;
}

export interface SignInSummary {
  session: ClassroomSession;
  stats: {
    total: number;
    signed: number;
    normal: number;
    late: number;
    absent: number;
    unsigned: number;
  };
  records: SignInRecord[];
  backup_results?: Array<Record<string, unknown>>;
}

export interface StudentSignInResult {
  id: number;
  session_id: number;
  student_id: number;
  student_number: string;
  student_name: string;
  status: "normal" | "late" | "absent";
  sign_time: string | null;
  duplicate: boolean;
}

export function startClassroomSession(sessionId: number) {
  return request<ClassroomSession>(`/classroom/sessions/${sessionId}/start`, {
    method: "POST"
  });
}

export function endClassroomSession(sessionId: number) {
  return request<SignInSummary>(`/classroom/sessions/${sessionId}/end`, {
    method: "POST"
  });
}

export function fetchSignInSummary(sessionId: number) {
  return request<SignInSummary>(`/classroom/sessions/${sessionId}/sign-ins`);
}

export function updateSignInStatus(sessionId: number, studentPk: number, status: "normal" | "late" | "absent", reason?: string) {
  return request<SignInSummary>(`/classroom/sessions/${sessionId}/sign-ins/status`, {
    method: "PUT",
    body: JSON.stringify({ student_pk: studentPk, status, reason })
  });
}

export function fetchSignInLogs(sessionId: number) {
  return request<Array<Record<string, unknown>>>(`/classroom/sessions/${sessionId}/sign-ins/logs`);
}

export function downloadSignIns(sessionId: number) {
  return downloadFile(`/classroom/sessions/${sessionId}/sign-ins.csv`, `session_${sessionId}_sign_ins.csv`);
}

export function fetchPublicSession(sessionId: number) {
  return request<ClassroomSession>(`/classroom/sessions/${sessionId}`);
}

export function fetchActiveSessions() {
  return request<ClassroomSession[]>("/classroom/sessions/active/list");
}

export function studentSignIn(sessionId: number, studentId: string, name: string) {
  return request<StudentSignInResult>(`/classroom/sessions/${sessionId}/sign-in`, {
    method: "POST",
    body: JSON.stringify({ student_id: studentId, name })
  });
}
