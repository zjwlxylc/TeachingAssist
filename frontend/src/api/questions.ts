import { downloadFile, request } from "./http";

export type QuestionType = "single_choice" | "multiple_choice" | "true_false" | "fill_blank" | "short_answer";

export interface QuestionOption {
  id?: number;
  option_key: string;
  content: string;
  is_correct?: number | boolean;
  display_order?: number;
}

export interface Question {
  id: number;
  session_id: number;
  title: string;
  content: string;
  question_type: QuestionType;
  status: string;
  start_time: string | null;
  deadline: string | null;
  score: number;
  created_at: string;
  published_at: string | null;
  updated_at: string;
  correct_answer?: string[] | string | null;
  keywords?: string[];
  options: QuestionOption[];
}

export interface QuestionStats {
  question: Question;
  total_students: number;
  submitted_count: number;
  draft_count: number;
  correct_count: number;
  correct_rate: number;
  option_distribution: Record<string, number>;
  typical_answers: Array<{ answer: string; count: number }>;
  answers: Array<Record<string, unknown>>;
}

export interface BonusSummary {
  settings: Record<string, number | string>;
  records: Array<Record<string, unknown>>;
}

export interface QuestionPublishedMessage {
  type: "question.published";
  session_id: number;
  question: Question;
}

export interface QuestionAnswerUpdatedMessage {
  type: "question.answer.updated";
  session_id: number;
  question_id: number;
  student_id: string;
  status: string;
}

export function fetchQuestions(sessionId: number) {
  return request<Question[]>(`/questions/sessions/${sessionId}`);
}

export function fetchPublicQuestions(sessionId: number) {
  return request<Question[]>(`/questions/sessions/${sessionId}/public`);
}

export function publishQuestion(
  sessionId: number,
  payload: {
    title: string;
    content: string;
    question_type: QuestionType;
    options?: QuestionOption[];
    correct_answer?: unknown;
    keywords?: string[];
    score?: number;
    start_time?: string;
    deadline?: string;
  }
) {
  return request<Question>(`/questions/sessions/${sessionId}`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function submitQuestionAnswer(
  questionId: number,
  payload: {
    student_id: string;
    name: string;
    answer: unknown;
    action?: "start_answer" | "save_draft" | "submit_answer" | "timeout_submit" | "view_feedback";
  }
) {
  return request<Record<string, unknown>>(`/questions/${questionId}/answers`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function fetchQuestionStats(questionId: number) {
  return request<QuestionStats>(`/questions/${questionId}/stats`);
}

export function fetchAnonymousQuestionStats(questionId: number) {
  return request<Omit<QuestionStats, "answers"> & { anonymous: boolean }>(`/questions/${questionId}/stats/anonymous`);
}

export function fetchQuestionDraft(questionId: number, studentId: string, name: string, token?: string | null) {
  const body: Record<string, unknown> = { student_id: studentId, name };
  if (token) {
    body.token = token;
  }
  return request<Record<string, unknown>>(`/questions/${questionId}/draft`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export interface MyAnswerFeedback {
  question_id: number;
  title: string;
  question_type: string;
  score: number;
  answer_text: string | null;
  status: string | null;
  is_correct: number | null;
  answer_score: number | null;
  submitted_at: string | null;
  quality_score: number | null;
  ai_feedback_status: string | null;
  ai_feedback: Record<string, unknown> | null;
}

export function fetchMyAnswers(sessionId: number, studentId: string, name: string, token?: string | null) {
  const params = new URLSearchParams({ student_id: studentId, name });
  if (token) {
    params.set("token", token);
  }
  return request<{ answers: MyAnswerFeedback[] }>(`/questions/sessions/${sessionId}/my-answers?${params.toString()}`);
}

export function fetchQuestionBonusSummary(sessionId: number) {
  return request<BonusSummary>(`/questions/sessions/${sessionId}/bonus`);
}

export function fetchQuestionBonusSettings() {
  return request<Record<string, number | string>>("/questions/bonus/settings");
}

export function updateQuestionBonusSettings(payload: Record<string, number>) {
  return request<Record<string, number | string>>("/questions/bonus/settings", {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function downloadQuestionAnswers(sessionId: number) {
  return downloadFile(`/questions/sessions/${sessionId}/answers.csv`, `session_${sessionId}_answers.csv`);
}

export interface StudentAnswerDetail {
  answer_id: number;
  student_id: number;
  student_number: string;
  student_name: string;
  answer_text: string;
  answer_json: unknown;
  status: string;
  is_correct: number | null;
  answer_score: number | null;
  quality_score: number | null;
  bonus_total: number | null;
  submitted_at: string | null;
  ai_feedback_status: string | null;
  ai_feedback: Record<string, unknown> | null;
}

export interface QuestionAnswersDetail {
  question: Record<string, unknown>;
  answers: StudentAnswerDetail[];
  total: number;
}

export function fetchQuestionAnswers(questionId: number) {
  return request<QuestionAnswersDetail>(`/questions/${questionId}/answers`);
}

export function setAnswerQualityScore(answerId: number, qualityScore: number) {
  return request<Record<string, unknown>>(`/questions/answers/${answerId}/quality-score`, {
    method: "PUT",
    body: JSON.stringify({ quality_score: qualityScore })
  });
}
