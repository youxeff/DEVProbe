import type {
  Analytics,
  ScanPage,
  ChangedFile,
  PullRequest,
  Repository,
  Scan,
  ScanStatus,
} from "@/types";

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
    response = await fetch(`/api/backend${path}`, {
      credentials: "same-origin",
      ...options,
      headers: { "Content-Type": "application/json", ...options.headers },
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
