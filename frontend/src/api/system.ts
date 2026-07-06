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
  ai?: {
    status: string;
    message?: string;
    basic_mode?: boolean;
  };
}

export interface NetworkCandidate {
  name: string;
  ip: string;
  selected: boolean;
}

export interface AccessInfo {
  candidates: NetworkCandidate[];
  selected_ip: string;
  port: number;
  access_url: string;
  port_status: {
    port: number;
    available: boolean;
    fallback_used: boolean;
  };
  firewall: {
    port: number;
    rule_exists: boolean;
    status: string;
    message: string;
    admin_command: string;
  };
}

export interface BackupRecord {
  id: number;
  backup_type: string;
  target: string;
  file_path: string;
  file_size: number;
  status: string;
  message: string | null;
  created_at: string;
}

export function fetchHealth() {
  return request<HealthStatus>("/health");
}

export function fetchStartupStatus() {
  return request<StartupStatus>("/system/startup");
}

export function fetchAccessInfo() {
  return request<AccessInfo>("/system/access");
}

export function updateAccessInfo(selectedIp: string, selectedPort?: number) {
  return request<AccessInfo>("/system/access", {
    method: "POST",
    body: JSON.stringify({ selected_ip: selectedIp, selected_port: selectedPort })
  });
}

export function fetchBackups() {
  return request<BackupRecord[]>("/system/backups");
}

export function createBackup() {
  return request<Array<{ target: string; file_path: string; file_size?: number; status: string; message?: string }>>(
    "/system/backups",
    { method: "POST" }
  );
}
