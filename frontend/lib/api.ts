import type {
  Analytics,
  ScanPage,
  ChangedFile,
  PullRequest,
  Repository,
  Scan,
  ScanStatus,
} from "@/types";
import type {
  AuthSession,
  Organization,
  Member,
  Usage,
  GitHubSettings,
  BillingStatus,
  AuditEvent,
  Role,
} from "@/types/account";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public scanId?: number,
  ) {
    super(message);
  }
}

export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    const csrf =
      typeof document === "undefined"
        ? ""
        : document.cookie
            .split("; ")
            .find((row) => row.startsWith("dp_csrf="))
            ?.split("=")[1];
    const org =
      typeof localStorage === "undefined"
        ? null
        : localStorage.getItem("devprobe-organization");
    response = await fetch(`/api/backend${path}`, {
      credentials: "same-origin",
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(csrf ? { "X-CSRF-Token": csrf } : {}),
        ...(org ? { "X-Organization-ID": org } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new ApiError(
      "Cannot reach DevProbe. Check your connection and try again.",
      0,
    );
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok)
    throw new ApiError(
      typeof body.detail === "string"
        ? body.detail
        : "The request could not be completed. Check your input and try again.",
      response.status,
      body.scan_id,
    );
  return body as T;
}
export const post = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });
export const api = {
  session: () => request<AuthSession>("/auth/session"),
  login: (body: { email: string; password: string }) =>
    post("/auth/login", body),
  register: (body: {
    email: string;
    password: string;
    name: string;
    organization_name: string;
  }) => post("/auth/register", body),
  logout: () => post("/auth/logout", {}),
  changePassword: (current_password: string, new_password: string) =>
    post("/auth/password", { current_password, new_password }),
  createOrganization: (name: string) =>
    post<Organization>("/organizations", { name }),
  members: () => request<Member[]>("/organizations/members"),
  invite: (email: string, role: Exclude<Role, "owner">) =>
    post<{ invite_url: string }>("/organizations/invitations", { email, role }),
  acceptInvitation: (token: string) =>
    post<{ organization_id: number }>("/organizations/invitations/accept", {
      token,
    }),
  changeMember: (id: number, role: Role) =>
    request(`/organizations/members/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    }),
  removeMember: (id: number) =>
    request(`/organizations/members/${id}`, { method: "DELETE" }),
  usage: () => request<Usage>("/organizations/usage"),
  audit: () => request<AuditEvent[]>("/organizations/audit"),
  githubSettings: () => request<GitHubSettings>("/github"),
  connectInstallation: (installation_id: number) =>
    post<{ url: string }>("/github/connect", { installation_id }),
  updateInstallation: (id: number, publish_checks: boolean) =>
    request(`/github/installations/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ publish_checks }),
    }),
  disconnectInstallation: (id: number) =>
    request(`/github/installations/${id}`, { method: "DELETE" }),
  publishCheck: (id: number) =>
    post<{ check_run_id: number }>(`/github/scans/${id}/check`, {}),
  billing: () => request<BillingStatus>("/billing"),
  checkout: () => post<{ url: string }>("/billing/checkout", {}),
  billingPortal: () => post<{ url: string }>("/billing/portal", {}),
  analytics: () => request<Analytics>("/analytics"),
  scans: (offset = 0) => request<ScanPage>(`/scans?offset=${offset}&limit=25`),
  health: () => request<{ status: string }>("/health"),
  repositories: () => request<Repository[]>("/repositories"),
  repository: (id: string | number) =>
    request<Repository>(`/repositories/${id}`),
  connect: (repo_url: string) =>
    post<Repository>("/repositories/metadata", { repo_url }),
  pulls: (repo_url: string) =>
    post<{ pulls: PullRequest[] }>("/pull-requests", { repo_url }),
  pull: (repo_url: string, number: number) =>
    post<PullRequest>(`/pull-requests/${number}`, { repo_url }),
  files: (repo_url: string, number: number) =>
    post<{ files: ChangedFile[] }>(`/pull-requests/${number}/files`, {
      repo_url,
    }),
  createScan: (repo_url: string, pr_number: number) =>
    post<{ scan_id: number; status: ScanStatus }>("/scans", {
      repo_url,
      pr_number,
    }),
  scan: (id: string | number) => request<Scan>(`/scans/${id}`),
  history: (id: string | number) =>
    request<Scan[]>(`/repositories/${id}/scans`),
};
