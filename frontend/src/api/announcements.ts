import { request } from "./http";

export interface Announcement {
  id: number;
  session_id: number;
  sender_role: string;
  sender_name: string;
  content: string;
  is_pinned: number;
  is_deleted: number;
  created_at: string;
  updated_at: string;
}

export interface AnnouncementMessage {
  type: "announcement.created";
  session_id: number;
  announcement: Announcement;
}

export function fetchAnnouncements(sessionId: number, lastMessageId?: number) {
  const query = lastMessageId ? `?last_message_id=${lastMessageId}` : "";
  return request<Announcement[]>(`/announcements/sessions/${sessionId}${query}`);
}

export function publishAnnouncement(sessionId: number, content: string) {
  return request<Announcement>(`/announcements/sessions/${sessionId}`, {
    method: "POST",
    body: JSON.stringify({ content })
  });
}

export function classroomSocketUrl(sessionId: number) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/classroom/${sessionId}`;
}
