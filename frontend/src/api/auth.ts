import { request, setAuthToken } from "./http";

export interface AuthStatus {
  password_set: boolean;
  locked: boolean;
  locked_until: string | null;
  failed_login_count: number;
}

export interface LoginResult {
  token: string;
  token_type: string;
  expires_at: string;
  teacher: {
    id: number;
    name: string;
  };
}

export function fetchAuthStatus() {
  return request<AuthStatus>("/auth/status");
}

export async function setupPassword(password: string, confirmPassword: string) {
  const result = await request<LoginResult>("/auth/setup", {
    method: "POST",
    body: JSON.stringify({ password, confirm_password: confirmPassword })
  });
  setAuthToken(result.token);
  return result;
}

export async function login(password: string) {
  const result = await request<LoginResult>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ password })
  });
  setAuthToken(result.token);
  return result;
}

export async function logout() {
  const result = await request<{ logged_out: boolean }>("/auth/logout", { method: "POST" });
  setAuthToken(null);
  return result;
}
