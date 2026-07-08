import { request } from "./http";

export interface AiProvider {
  id: number;
  provider_name: string;
  display_name: string;
  base_url: string;
  model_name: string;
  http_proxy: string | null;
  enabled: boolean;
  is_active: boolean;
  last_status: "unknown" | "available" | "unavailable" | "disabled";
  last_checked_at: string | null;
  last_error: string | null;
  api_key_set: boolean;
  api_key_masked: string | null;
}

export interface AiSafetySettings {
  id: number;
  max_length: number;
  blocked_keywords: string[];
  keyword_action: "replace" | "block";
  display_strategy: "review_first" | "direct_with_report";
  interaction_moderation_enabled: boolean;
  updated_at: string;
}

export interface AiDegradationStrategy {
  scenario: string;
  normal_mode: string;
  degraded_mode: string;
  affected_features: string[];
  base_flow_available: boolean;
}

export interface AiCheckLog {
  id: number;
  provider_id: number | null;
  provider_display_name: string | null;
  status: "available" | "unavailable" | "disabled";
  message: string | null;
  latency_ms: number | null;
  checked_at: string;
}

export interface AiOverview {
  status: "unknown" | "available" | "unavailable" | "disabled";
  basic_mode: boolean;
  active_provider: AiProvider | null;
  providers: AiProvider[];
  safety: AiSafetySettings;
  degradation_strategies: AiDegradationStrategy[];
  recent_checks: AiCheckLog[];
  affected_features: string[];
}

export interface AiProviderPayload {
  provider_name: string;
  display_name: string;
  base_url: string;
  model_name: string;
  api_key?: string;
  http_proxy?: string;
  enabled: boolean;
  clear_api_key?: boolean;
}

export interface AiConnectivityResult {
  log_id: number;
  status: "available" | "unavailable" | "disabled";
  message: string;
  latency_ms: number;
  provider: AiProvider;
  basic_mode: boolean;
}

export interface AiSafetyCheckResult {
  safe: boolean;
  blocked: boolean;
  action: "pass" | "replace" | "block" | "truncate";
  matched_keywords: string[];
  original_length: number;
  sanitized_length: number;
  text: string;
  display_strategy: "review_first" | "direct_with_report";
  message: string;
}

export interface AiFailureTask {
  id: number;
  scenario: string;
  source_type: string | null;
  source_id: number | null;
  status: "pending_manual" | "template_generated" | "resolved";
  reason: string | null;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export function fetchAiOverview() {
  return request<AiOverview>("/ai/overview");
}

export function createAiProvider(payload: AiProviderPayload) {
  return request<AiProvider>("/ai/providers", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateAiProvider(providerId: number, payload: AiProviderPayload) {
  return request<AiProvider>(`/ai/providers/${providerId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function activateAiProvider(providerId: number) {
  return request<AiProvider>(`/ai/providers/${providerId}/activate`, { method: "POST" });
}

export function checkAiConnectivity(providerId?: number) {
  return request<AiConnectivityResult>("/ai/check", {
    method: "POST",
    body: JSON.stringify({ provider_id: providerId })
  });
}

export function updateAiSafety(settings: Omit<AiSafetySettings, "id" | "updated_at">) {
  return request<AiSafetySettings>("/ai/safety", {
    method: "PUT",
    body: JSON.stringify(settings)
  });
}

export function checkAiSafety(text: string, keywords?: string[]) {
  return request<AiSafetyCheckResult>("/ai/safety/check", {
    method: "POST",
    body: JSON.stringify({ text, source_type: "manual_test", blocked_keywords: keywords })
  });
}

export function fetchAiFailureTasks() {
  return request<AiFailureTask[]>("/ai/failure-tasks");
}

export function toggleModerationEnabled(enabled: boolean) {
  return request<AiSafetySettings>("/ai/safety/moderation", {
    method: "PUT",
    body: JSON.stringify({ enabled })
  });
}

export interface AiChatMessage {
  role: string;
  content: string;
}

export interface AiChatResult {
  reply: string;
  intent: string;
  guarded: boolean;
}

export function chatWithAi(sessionId: number, messages: AiChatMessage[]) {
  return request<AiChatResult>("/ai/chat", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, messages })
  });
}

export function studentChatWithAi(
  sessionId: number,
  studentId: string,
  name: string,
  messages: AiChatMessage[]
) {
  return request<AiChatResult>("/ai/student-chat", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, student_id: studentId, name, messages })
  });
}
