export type Severity = "critical" | "high" | "medium" | "low" | "info";
export type Category =
  | "security"
  | "complexity"
  | "style"
  | "testing"
  | "maintainability"
  | "documentation";
export interface Issue {
  file_path: string;
  line_number: number | null;
  tool: string;
  category: Category;
  severity: Severity;
  message: string;
  recommendation: string;
  rule_id: string | null;
}
export interface Contributor {
  login: string | null;
  avatar_url: string | null;
  contributions: number;
}
export interface Repository {
  id: number;
  github_repo_id: number | null;
  owner: string;
  name: string;
  full_name: string;
  description: string | null;
  html_url: string;
  default_branch: string | null;
  language: string | null;
  stars: number;
  forks: number;
  open_issues: number;
  contributors: Contributor[];
}
export interface PullRequest {
  number: number;
  title: string;
  author: string | null;
  state: string;
  html_url: string;
  created_at: string;
  updated_at: string;
}
export interface ChangedFile {
  filename: string;
  status: string;
  additions: number;
  deletions: number;
  changes: number;
  patch: string | null;
}
export type ScanStatus = "pending" | "running" | "completed" | "failed";
export interface AIReview {
  summary: string;
  risks: string[];
  suggested_tests: string[];
  recommended_fixes: string[];
  model_name: string;
  input_tokens: number;
  output_tokens: number;
  estimated_cost: number | null;
}
export interface Scan {
  ai_status: "disabled" | "completed" | "failed";
  ai_review: AIReview | null;
  tool_executions: {
    tool: string;
    status: string;
    duration_seconds: number;
    files_supplied: number;
  }[];
  id: number;
  repository_id: number | null;
  repo_url: string;
  pr_number: number;
  status: ScanStatus;
  trigger_source: string;
  head_sha: string | null;
  risk_score: number | null;
  risk_level: "Low" | "Medium" | "High" | "Critical" | null;
  changed_files_count: number;
  additions: number;
  deletions: number;
  total_changed_lines: number;
  total_issues: number;
  security_count: number;
  complexity_count: number;
  style_count: number;
  testing_count: number;
  maintainability_count: number;
  documentation_count: number;
  scan_duration_seconds: number | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  failure_reason: string | null;
  issues: Issue[];
  analysis_warnings: string[];
}

export interface Analytics {
  total_scans: number;
  completed_scans: number;
  failed_scans: number;
  prs_analyzed: number;
  files_analyzed: number;
  changed_lines_analyzed: number;
  total_issues: number;
  average_risk_score: number | null;
  average_duration_seconds: number | null;
  failure_rate: number;
  ai_reviews: number;
  ai_input_tokens: number;
  ai_output_tokens: number;
  ai_estimated_cost: number | null;
  severity_counts: Record<string, number>;
  category_counts: Record<string, number>;
  trend: {
    scan_id: number;
    created_at: string;
    risk_score: number;
    total_issues: number;
  }[];
}
export interface ScanPage {
  items: Scan[];
  total: number;
  offset: number;
  limit: number;
}
