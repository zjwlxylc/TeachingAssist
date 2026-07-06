export interface ApiResponse<T> {
  success: boolean;
  code: string;
  message: string;
  data: T;
}

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

let authToken: string | null = localStorage.getItem("teacher_token");

export function setAuthToken(token: string | null) {
  authToken = token;
  if (token) {
    localStorage.setItem("teacher_token", token);
  } else {
    localStorage.removeItem("teacher_token");
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...(init?.headers ?? {})
    },
    ...init
  });

  const payload = (await response.json()) as ApiResponse<T>;
  if (!response.ok || !payload.success) {
    throw new Error(payload.message || "请求失败");
  }
  return payload.data;
}

export async function downloadFile(path: string, fallbackName: string) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {})
    }
  });
  if (!response.ok) {
    throw new Error("文件下载失败");
  }
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^"]+)"?/i);
  const fileName = match?.[1] || fallbackName;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
