import { request } from "./http";

export interface HealthStatus {
  status: string;
  app_name: string;
  environment: string;
  database_path: string;
  database_integrity: string;
}

export interface StartupStatus {
  directories: string[];
  database_path: string;
  migrations: string[];
  integrity: string;
  removable_root: string | null;
}

export function fetchHealth() {
  return request<HealthStatus>("/health");
}

export function fetchStartupStatus() {
  return request<StartupStatus>("/system/startup");
}
