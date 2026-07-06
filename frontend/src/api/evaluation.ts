import { downloadFile, request } from "./http";

export interface EvaluationReport {
  session: Record<string, unknown>;
  weights: Record<string, number | string>;
  version_type?: string;
  version_no?: number;
  summary: {
    total?: number;
    level_distribution?: Record<string, number>;
    attendance_rate?: number;
    average_score?: number;
    warnings?: Array<Record<string, unknown>>;
  };
  records: Array<Record<string, unknown>>;
}

export function calculateEvaluation(sessionId: number, versionType: "temporary" | "final" = "temporary") {
  return request<EvaluationReport>(`/evaluation/sessions/${sessionId}/calculate`, {
    method: "POST",
    body: JSON.stringify({ version_type: versionType })
  });
}

export function fetchEvaluationReport(sessionId: number) {
  return request<EvaluationReport>(`/evaluation/sessions/${sessionId}`);
}

export function updateEvaluationWeights(payload: Record<string, number>) {
  return request<Record<string, number | string>>("/evaluation/weights", {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function fetchStudentEvaluationFeedback(sessionId: number, studentId: string, name: string) {
  return request<Record<string, unknown>>(`/evaluation/sessions/${sessionId}/student-feedback`, {
    method: "POST",
    body: JSON.stringify({ student_id: studentId, name })
  });
}

export function downloadEvaluationReport(sessionId: number) {
  return downloadFile(`/evaluation/sessions/${sessionId}.csv`, `session_${sessionId}_evaluation.csv`);
}
