import { request } from "./http";

export interface PrivateMessage {
  id: number;
  sender_role: "teacher" | "student";
  sender_student_id: number | null;
  sender_name: string;
  receiver_role: "teacher" | "student";
  receiver_student_id: number | null;
  content: string;
  is_deleted: number;
  read_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MessageCreated {
  type: "message.created";
  message: PrivateMessage;
}

export interface ConversationSummary {
  student_pk: number;
  student_number: string;
  student_name: string;
  class_name: string | null;
  last_message: string;
  last_at: string;
  unread_count: number;
  total_count: number;
}

export interface ThreadStudent {
  id: number;
  student_id: string;
  name: string;
}

export interface TeacherThread {
  student: ThreadStudent;
  messages: PrivateMessage[];
}

export function messageSocketUrl(token?: string, studentId?: string, name?: string) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const params = new URLSearchParams();
  if (token) {
    params.set("token", token);
  }
  if (studentId) {
    params.set("student_id", studentId);
  }
  if (name) {
    params.set("name", name);
  }
  return `${protocol}//${window.location.host}/ws/messages?${params.toString()}`;
}

export function sendStudentMessage(studentId: string, name: string, content: string, token?: string | null) {
  return request<PrivateMessage>(`/messages`, {
    method: "POST",
    body: JSON.stringify({ student_id: studentId, name, content, token: token ?? undefined })
  });
}

export function fetchStudentThread(studentId: string, name: string, token?: string | null) {
  const params = new URLSearchParams({ student_id: studentId, name });
  if (token) {
    params.set("token", token);
  }
  return request<PrivateMessage[]>(`/messages/mine?${params.toString()}`);
}

export function markStudentMessagesRead(token?: string | null) {
  const params = new URLSearchParams();
  if (token) {
    params.set("token", token);
  }
  return request<{ updated: number }>(`/messages/mine/read?${params.toString()}`, {
    method: "POST"
  });
}

export function markTeacherMessagesRead(studentId: number) {
  return request<{ updated: number }>(`/messages/students/${studentId}/read`, {
    method: "POST"
  });
}

export function fetchConversations() {
  return request<ConversationSummary[]>(`/messages/conversations`);
}

export function fetchTeacherThread(studentId: number) {
  return request<TeacherThread>(`/messages/students/${studentId}`);
}

export function replyToStudent(studentId: number, content: string) {
  return request<PrivateMessage>(`/messages/students/${studentId}/reply`, {
    method: "POST",
    body: JSON.stringify({ content })
  });
}

export function fetchUnreadCount() {
  return request<{ unread_count: number }>(`/messages/unread-count`);
}
