import { request } from "./http";

export interface Course {
  id: number;
  name: string;
  teacher_id: number | null;
  teacher_name: string | null;
  class_count?: number;
  student_count?: number;
  created_at: string;
  updated_at: string;
}

export interface ClassGroup {
  id: number;
  name: string;
  student_count?: number;
  created_at: string;
  updated_at: string;
}

export interface ClassroomSession {
  id: number;
  course_id: number;
  class_id: number;
  title: string;
  session_no: number;
  status: string;
  start_time: string | null;
  end_time: string | null;
  is_makeup: number;
  schedule_note: string | null;
  course_name?: string;
  class_name?: string;
  roster_count?: number;
}

export interface Student {
  id: number;
  student_id: string;
  name: string;
  class_id: number;
  class_name: string;
  major: string | null;
  college: string | null;
  grade: string | null;
}

export interface ImportJob {
  job_id: number;
  file_name: string;
  file_size: number;
  headers: string[];
  sample_rows: Array<Record<string, string>>;
  total_rows: number;
  standard_fields: Record<string, string>;
  required_fields: string[];
}

export interface ImportPreviewRow {
  row_number: number;
  data: Record<string, string>;
  errors: string[];
  warnings: string[];
  valid: boolean;
}

export interface ImportPreview {
  job_id: number;
  total_rows: number;
  valid_rows: number;
  error_count: number;
  warning_count: number;
  rows: ImportPreviewRow[];
}

export function fetchCourses() {
  return request<Course[]>("/academic/courses");
}

export function createCourse(name: string, teacherName?: string) {
  return request<Course>("/academic/courses", {
    method: "POST",
    body: JSON.stringify({ name, teacher_name: teacherName || undefined })
  });
}

export function fetchClasses(courseId?: number) {
  const query = courseId ? `?course_id=${courseId}` : "";
  return request<ClassGroup[]>(`/academic/classes${query}`);
}

export function createClass(name: string) {
  return request<ClassGroup>("/academic/classes", {
    method: "POST",
    body: JSON.stringify({ name })
  });
}

export function linkCourseClass(courseId: number, classId: number) {
  return request<{ id: number; course_id: number; class_id: number }>("/academic/course-classes", {
    method: "POST",
    body: JSON.stringify({ course_id: courseId, class_id: classId })
  });
}

export function fetchSessions(courseId?: number) {
  const query = courseId ? `?course_id=${courseId}` : "";
  return request<ClassroomSession[]>(`/academic/sessions${query}`);
}

export function createSession(payload: {
  course_id: number;
  class_id: number;
  title: string;
  session_no: number;
  start_time?: string;
  end_time?: string;
  is_makeup?: boolean;
  schedule_note?: string;
}) {
  return request<ClassroomSession>("/academic/sessions", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function fetchStudents(courseId?: number, classId?: number) {
  const params = new URLSearchParams();
  if (courseId) params.set("course_id", String(courseId));
  if (classId) params.set("class_id", String(classId));
  const query = params.toString();
  return request<Student[]>(`/academic/students${query ? `?${query}` : ""}`);
}

export async function uploadStudentExcel(file: File) {
  const form = new FormData();
  form.append("file", file);
  return request<ImportJob>("/academic/imports/excel", {
    method: "POST",
    headers: {},
    body: form
  });
}

export function previewStudentImport(jobId: number, mapping: Record<string, string>) {
  return request<ImportPreview>(`/academic/imports/${jobId}/preview`, {
    method: "POST",
    body: JSON.stringify({ mapping })
  });
}

export function confirmStudentImport(
  jobId: number,
  courseId: number,
  mapping: Record<string, string>,
  importValidOnly = true
) {
  return request<{ imported: number; skipped: number; failed: number; total: number }>(
    `/academic/imports/${jobId}/confirm`,
    {
      method: "POST",
      body: JSON.stringify({ course_id: courseId, mapping, import_valid_only: importValidOnly })
    }
  );
}
