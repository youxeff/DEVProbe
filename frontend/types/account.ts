export type Role = "owner" | "admin" | "member" | "viewer";
export interface Organization {
  id: number;
  name: string;
  plan: "free" | "pro";
  role: Role;
}
export interface AuthSession {
  enabled: boolean;
  registration_enabled: boolean;
  user: { id: number; email: string; name: string } | null;
  organizations: Organization[];
  active_organization: Organization | null;
}
export interface Member {
  id: number;
  user_id: number;
  name: string;
  email: string;
  role: Role;
}
export interface Usage {
  plan: string;
  period: string;
  scans: number;
  repositories: number;
  members: number;
  limits: { scans: number; repositories: number; members: number };
}
export interface GitHubSettings {
  configured: boolean;
  install_url: string | null;
  installations: {
    id: number;
    github_installation_id: number;
    account_login: string;
    active: boolean;
    publish_checks: boolean;
  }[];
}
export interface BillingStatus {
  configured: boolean;
  status: string;
  has_customer: boolean;
}
export interface AuditEvent {
  id: number;
  action: string;
  resource_id: string | null;
  user_id: number | null;
  created_at: string;
}
