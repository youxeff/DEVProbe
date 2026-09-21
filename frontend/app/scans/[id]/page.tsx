"use client";
import { use } from "react";
import Link from "next/link";
import useSWR from "swr";
import {
  ArrowLeft,
  FileCode,
  Clock3,
  Bug,
  GitCompareArrows,
  LoaderCircle,
  AlertCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import { number, duration, date } from "@/lib/utils";
import { PageHeading, LoadingState, ErrorState } from "@/components/States";
import { StatCard } from "@/components/Stats";
import { AIReviewCard } from "@/components/AIReviewCard";
import { PublishCheck } from "@/components/PublishCheck";
import { RiskScoreCard } from "@/components/RiskScoreCard";
import { IssueTable } from "@/components/IssueTable";
import { IssueChart } from "@/components/IssueCharts";
export default function ScanPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const {
    data: scan,
    error,
    mutate,
  } = useSWR(["scan", id], () => api.scan(id), {
    refreshInterval: (data) =>
      !data || ["pending", "running"].includes(data.status) ? 1500 : 0,
    shouldRetryOnError: false,
  });
  if (error) return <ErrorState error={error} retry={() => mutate()} />;
  if (!scan) return <LoadingState label="Loading scan results…" />;
  return (
    <>
      <Link href={`/repositories/${scan.repository_id}`} className="back-link">
        <ArrowLeft size={13} />
        Back to repository
      </Link>
      <PageHeading
        eyebrow={`Scan #${scan.id} · PR #${scan.pr_number}`}
        title="A clearer view of this change."
        description={`${scan.repo_url.replace("https://github.com/", "")} · ${date(scan.created_at)}`}
        action={
          <span className={`status-badge status-${scan.status}`}>
            {scan.status}
          </span>
        }
      />
      {["pending", "running"].includes(scan.status) ? (
        <div className="state-card" role="status">
          <LoaderCircle size={27} className="spin" />
          <h2>
            {scan.status === "pending"
              ? "Your scan is queued"
              : "Analyzing pull request changes"}
          </h2>
          <p>This page updates automatically. You can return at any time.</p>
        </div>
      ) : scan.status === "failed" ? (
        <div className="state-card error-state" role="alert">
          <AlertCircle />
          <h2>This scan could not finish</h2>
          <p>{scan.failure_reason}</p>
          <Link href={`/pull-requests/${scan.repository_id}/${scan.pr_number}`}>
            Return to the pull request to retry →
          </Link>
        </div>
      ) : (
        <>
          <div className="scan-summary">
            <RiskScoreCard scan={scan} />
            <div className="stats-grid">
              <StatCard
                label="Total findings"
                value={number(scan.total_issues)}
                icon={Bug}
              />
              <StatCard
                label="Changed files"
                value={number(scan.changed_files_count)}
                icon={FileCode}
              />
              <StatCard
                label="Changed lines"
                value={number(scan.total_changed_lines)}
                icon={GitCompareArrows}
              />
              <StatCard
                label="Scan duration"
                value={duration(scan.scan_duration_seconds)}
                icon={Clock3}
              />
            </div>
          </div>
          <div className="two-column">
            <IssueChart issues={scan.issues} dimension="severity" />
            <IssueChart issues={scan.issues} dimension="category" />
          </div>
          <div className="section-heading">
            <div>
              <h2>Review findings</h2>
              <p>Follow each signal back to the code.</p>
            </div>
            <span className="status-badge">{scan.total_issues} findings</span>
          </div>
          <IssueTable issues={scan.issues} />
          <AIReviewCard scan={scan} />
          <PublishCheck scanId={scan.id} />
          <details className="analysis-note">
            <summary>Analysis scope & limitations</summary>
            <ul>
              {scan.analysis_warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          </details>
        </>
      )}
    </>
  );
}
