import { downloadFile, request } from "./http";

export interface HomeworkAttachment {
  id: number;
  homework_id?: number;
  original_name: string;
  stored_name: string;
  file_path: string;
  file_size: number;
  mime_type: string | null;
  created_at: string;
}

export interface Homework {
  id: number;
  session_id: number;
  title: string;
  description: string | null;
  deadline: string;
  grading_criteria: string | null;
  status: "unpublished" | "active" | "closed" | "archived";
  allow_late: number | boolean;
  published_at: string | null;
  created_at: string;
  updated_at: string;
  attachments: HomeworkAttachment[];
}

export interface HomeworkSubmissionFile {
  id?: number;
  submission_id?: number;
  original_name: string;
  stored_name?: string;
  file_path?: string;
  file_size: number;
  mime_type?: string | null;
  created_at?: string;
}

export interface HomeworkSubmissionRecord {
  student_pk: number;
  student_number: string;
  student_name: string;
  submission_id: number | null;
  text_content: string | null;
  submission_status:
    | "not_submitted"
    | "submitted"
    | "late"
    | "pending_review"
    | "ai_reviewed"
    | "teacher_reviewed"
    | "published";
  submit_version: number | null;
  submitted_at: string | null;
  created_at: string | null;
  ai_score?: number | null;
  ai_feedback?: Record<string, unknown> | null;
  ai_confidence?: number | null;
  final_score?: number | null;
  final_feedback?: string | null;
  grade_published_at?: string | null;
  files: HomeworkSubmissionFile[];
}

export interface HomeworkSubmissionSummary {
  homework: Homework;
  stats: {
    total: number;
    submitted: number;
    not_submitted: number;
    late: number;
  };
  records: HomeworkSubmissionRecord[];
}

export interface HomeworkSubmitResult {
  id: number;
  homework_id: number;
  session_id: number;
  student_id: number;
  student_number: string;
  student_name: string;
  text_content: string | null;
  status: string;
  submit_version: number;
  is_latest: number;
  submitted_at: string;
  files: HomeworkSubmissionFile[];
}

export function fetchHomework(sessionId: number) {
  return request<Homework[]>(`/homework/sessions/${sessionId}`);
}

export function fetchPublicHomework(sessionId: number) {
  return request<Homework[]>(`/homework/sessions/${sessionId}/public`);
}

export function createHomework(
  sessionId: number,
  payload: {
    title: string;
    description?: string;
    deadline: string;
    grading_criteria?: string;
    allow_late?: boolean;
  }
) {
  return request<Homework>(`/homework/sessions/${sessionId}`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function submitHomework(
  homeworkId: number,
  payload: {
    student_id: string;
    name: string;
    text_content?: string;
    files?: File[];
  }
) {
  const formData = new FormData();
  formData.append("student_id", payload.student_id);
  formData.append("name", payload.name);
  formData.append("text_content", payload.text_content ?? "");
  payload.files?.forEach((file) => formData.append("files", file));
  return request<HomeworkSubmitResult>(`/homework/${homeworkId}/submissions`, {
    method: "POST",
    body: formData
  });
}

export function fetchHomeworkSubmissionSummary(homeworkId: number) {
  return request<HomeworkSubmissionSummary>(`/homework/${homeworkId}/submissions`);
}

export function addHomeworkAttachments(homeworkId: number, files: File[]) {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  return request<Homework>(`/homework/${homeworkId}/attachments`, {
    method: "POST",
    body: formData
  });
}

export function startHomeworkAiReview(homeworkId: number) {
  return request<Record<string, unknown>>(`/homework/${homeworkId}/ai-review`, {
    method: "POST"
  });
}

export function reviewHomeworkSubmission(submissionId: number, finalScore: number, finalFeedback?: string) {
  return request<Record<string, unknown>>(`/homework/submissions/${submissionId}/review`, {
    method: "PUT",
    body: JSON.stringify({ final_score: finalScore, final_feedback: finalFeedback })
  });
}

export function publishHomeworkGrades(homeworkId: number) {
  return request<Record<string, unknown>>(`/homework/${homeworkId}/publish-grades`, {
    method: "POST"
  });
}

export function fetchHomeworkFeedback(homeworkId: number, studentId: string, name: string) {
  return request<Record<string, unknown>>(`/homework/${homeworkId}/feedback`, {
    method: "POST",
    body: JSON.stringify({ student_id: studentId, name })
  });
}

export function downloadHomeworkSubmissions(homeworkId: number) {
  return downloadFile(`/homework/${homeworkId}/submissions.csv`, `homework_${homeworkId}_submissions.csv`);
}
