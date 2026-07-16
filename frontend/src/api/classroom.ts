import { ClassroomSession } from "./academic";
import { downloadFile, request } from "./http";
import { getBrowserSessionId } from "../utils/deviceFingerprint";

export interface SignInRecord {
  student_pk: number;
  student_number: string;
  student_name: string;
  class_name: string;
  record_id: number | null;
  status: "normal" | "late" | "absent" | "leave" | null;
  sign_time: string | null;
  ip_address: string | null;
  user_agent: string | null;
  device_hash?: string | null;
}

export interface SignInSummary {
  session: ClassroomSession;
  stats: {
    total: number;
    signed: number;
    normal: number;
    late: number;
    absent: number;
    leave: number;
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
  token?: string;
  device_warning?: {
    level: "warning" | "critical";
    message: string;
    device_shared: boolean;
    shared_with_count: number;
    ip_matched: boolean;
  };
}

export interface DeviceSharingAlert {
  id: number;
  session_id: number;
  device_hash: string;
  student_count: number;
  student_ids: number[];
  student_ids_json: string;
  alert_level: "warning" | "critical";
  reviewed: number;
  reviewed_by: string | null;
  reviewed_at: string | null;
  notes: string | null;
  created_at: string;
  student_list?: string;
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

export function updateSignInStatus(sessionId: number, studentPk: number, status: "normal" | "late" | "absent" | "leave", reason?: string) {
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
  let browserSessionId: string | null = null;
  try {
    browserSessionId = getBrowserSessionId();
  } catch {
    // 不可用时继续签到，不阻塞流程
  }
  return request<StudentSignInResult>(`/classroom/sessions/${sessionId}/sign-in`, {
    method: "POST",
    body: JSON.stringify({
      student_id: studentId,
      name,
      device_hash: browserSessionId,
    }),
  });
}

export function fetchDeviceAlerts(sessionId: number) {
  return request<DeviceSharingAlert[]>(`/classroom/sessions/${sessionId}/device-alerts`);
}

export function reviewDeviceAlert(alertId: number, notes?: string) {
  return request<DeviceSharingAlert>(`/classroom/device-alerts/${alertId}/review`, {
    method: "PUT",
    body: JSON.stringify({ notes: notes ?? null }),
  });
}

export interface EnrollmentApplication {
  id: number;
  session_id: number;
  student_number: string;
  name: string;
  major: string | null;
  college: string | null;
  grade: string | null;
  status: "pending" | "approved" | "rejected" | "auto_merged";
  rejection_reason: string | null;
  assigned_class_id: number | null;
  assigned_class_name: string | null;
  auto_signed_in: number;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
}

/** 跨课堂待审批注册申请（含所属课堂信息，用于教师端顶部汇总卡片） */
export interface EnrollmentApplicationWithSession extends EnrollmentApplication {
  session_title?: string;
  course_name?: string;
  class_name?: string;
}

/** 教师获取全部课堂的待审批注册申请（跨课堂汇总） */
export function fetchPendingEnrollments() {
  return request<EnrollmentApplicationWithSession[]>(`/classroom/enrollment/pending`);
}

export function createEnrollmentApplication(
  sessionId: number,
  studentId: string,
  name: string,
  major?: string,
  college?: string,
  grade?: string
) {
  let browserSessionId: string | null = null;
  try {
    browserSessionId = getBrowserSessionId();
  } catch {
    // 不阻塞流程
  }

  return request<EnrollmentApplication>(`/classroom/sessions/${sessionId}/enrollment/apply`, {
    method: "POST",
    body: JSON.stringify({
      student_id: studentId,
      name,
      major: major ?? null,
      college: college ?? null,
      grade: grade ?? null,
      device_hash: browserSessionId,
    }),
  });
}

export function fetchEnrollmentApplications(sessionId: number, status?: string) {
  const query = status ? `?status=${status}` : "";
  return request<EnrollmentApplication[]>(`/classroom/sessions/${sessionId}/enrollment/applications${query}`);
}

export function fetchSessionClasses(sessionId: number) {
  return request<Array<{id: number; name: string}>>(`/classroom/sessions/${sessionId}/enrollment/classes`);
}

export function approveEnrollmentApplication(
  sessionId: number,
  applicationId: number,
  classId: number,
  autoSignIn: boolean = true
) {
  return request<EnrollmentApplication>(`/classroom/sessions/${sessionId}/enrollment/applications/${applicationId}/approve`, {
    method: "POST",
    body: JSON.stringify({ class_id: classId, auto_sign_in: autoSignIn }),
  });
}

export function rejectEnrollmentApplication(
  sessionId: number,
  applicationId: number,
  rejectionReason?: string
) {
  return request<EnrollmentApplication>(`/classroom/sessions/${sessionId}/enrollment/applications/${applicationId}/reject`, {
    method: "POST",
    body: JSON.stringify({ rejection_reason: rejectionReason ?? null }),
  });
}
