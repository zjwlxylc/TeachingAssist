import { request } from "./http";

export interface InteractionSettings {
  session_id: number;
  student_messages_enabled: number | boolean;
  updated_at: string;
}

export interface InteractionMessage {
  id: number;
  session_id: number;
  sender_role: "teacher" | "student";
  sender_student_id: number | null;
  sender_name: string;
  content: string;
  is_deleted: number;
  created_at: string;
  updated_at: string;
}

export interface InteractionMessageCreated {
  type: "interaction.message.created";
  session_id: number;
  message: InteractionMessage;
}

export interface InteractionSettingsUpdated {
  type: "interaction.settings.updated";
  session_id: number;
  settings: InteractionSettings;
}

export interface InteractionModerated {
  type: "interaction.moderated";
  session_id: number;
  log_id: number;
  student_id: number;
  student_name: string;
  content: string;
  reason: string;
}

export interface InteractionModerationLog {
  id: number;
  session_id: number;
  student_id: number;
  student_name: string;
  content: string;
  reason: string | null;
  status: "pending" | "approved" | "rejected";
  reviewed_at: string | null;
  created_at: string;
}

export function fetchInteractionSettings(sessionId: number) {
  return request<InteractionSettings>(`/interactions/sessions/${sessionId}/settings`);
}

export function updateInteractionSettings(sessionId: number, studentMessagesEnabled: boolean) {
  return request<InteractionSettings>(`/interactions/sessions/${sessionId}/settings`, {
    method: "PUT",
    body: JSON.stringify({ student_messages_enabled: studentMessagesEnabled })
  });
}

export function fetchInteractionMessages(sessionId: number, lastMessageId?: number) {
  const query = lastMessageId ? `?last_message_id=${lastMessageId}` : "";
  return request<InteractionMessage[]>(`/interactions/sessions/${sessionId}/messages${query}`);
}

export function publishTeacherInteractionMessage(sessionId: number, content: string) {
  return request<InteractionMessage>(`/interactions/sessions/${sessionId}/messages/teacher`, {
    method: "POST",
    body: JSON.stringify({ content })
  });
}

export function publishStudentInteractionMessage(sessionId: number, studentId: string, name: string, content: string) {
  return request<InteractionMessage>(`/interactions/sessions/${sessionId}/messages/student`, {
    method: "POST",
    body: JSON.stringify({ student_id: studentId, name, content })
  });
}

export function fetchModerationLogs(sessionId: number, status?: string) {
  const query = status ? `?status=${status}` : "";
  return request<InteractionModerationLog[]>(`/interactions/sessions/${sessionId}/moderation/logs${query}`);
}

export function approveModerationLog(sessionId: number, logId: number) {
  return request<{ log_id: number; status: string; message: InteractionMessage | null }>(
    `/interactions/sessions/${sessionId}/moderation/${logId}/approve`,
    { method: "POST" }
  );
}

export function rejectModerationLog(sessionId: number, logId: number) {
  return request<{ log_id: number; status: string; message: InteractionMessage | null }>(
    `/interactions/sessions/${sessionId}/moderation/${logId}/reject`,
    { method: "POST" }
  );
}
