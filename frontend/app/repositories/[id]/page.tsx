"use client";
import { use } from "react";
import useSWR from "swr";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowUpRight,
  Star,
  GitFork,
  GitBranch,
  GitPullRequest,
} from "lucide-react";
import { api } from "@/lib/api";
import { number } from "@/lib/utils";
import { PageHeading, LoadingState, ErrorState } from "@/components/States";
import { StatCard } from "@/components/Stats";
import { PullRequestTable } from "@/components/PullRequestTable";
import { ScanHistoryTable } from "@/components/ScanHistoryTable";
import { Button } from "@/components/ui/button";
export default function RepositoryPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data, error, mutate } = useSWR(["repository", id], async () => {
    const repository = await api.repository(id);
    const [pulls, history] = await Promise.all([
      api.pulls(repository.html_url),
      api.history(id),
    ]);
    return { repository, pulls: pulls.pulls, history };
  });
  if (error) return <ErrorState error={error} retry={() => mutate()} />;
  if (!data)
    return <LoadingState label="Fetching repository and pull requests…" />;
  const { repository: r, pulls, history } = data;
  return (
    <>
      <Link className="back-link" href="/repositories">
        <ArrowLeft size={13} /> All repositories
      </Link>
      <PageHeading
        eyebrow="Repository overview"
        title={r.full_name}
        description={
          r.description ||
          "Explore this repository’s pull requests and analysis history."
        }
        action={
          <Button variant="outline" asChild>
            <a href={r.html_url} target="_blank" rel="noreferrer">
              View on GitHub <ArrowUpRight size={14} />
            </a>
          </Button>
        }
      />
      <div className="inline-meta">
        <span className="status-badge">{r.language || "Mixed languages"}</span>
        <span>Default branch · {r.default_branch}</span>
      </div>
      <div className="stats-grid">
        <StatCard label="Stars" value={number(r.stars)} icon={Star} />
        <StatCard label="Forks" value={number(r.forks)} icon={GitFork} />
        <StatCard
          label="Open pull requests"
          value={number(pulls.length)}
          icon={GitPullRequest}
        />
        <StatCard
          label="Open issues & PRs"
          value={number(r.open_issues)}
          icon={GitBranch}
        />
      </div>
      <div className="section-heading">
        <div>
          <h2>Pull requests</h2>
          <p>Choose a change to understand its impact.</p>
        </div>
        <span className="status-badge">{pulls.length} open</span>
      </div>
      <div className="panel">
        <PullRequestTable pulls={pulls} repoId={r.id} />
      </div>
      <div className="section-heading">
        <h2>Recent scans</h2>
      </div>
      <div className="panel">
        <ScanHistoryTable scans={history} />
      </div>
      {r.contributors.length > 0 && (
        <>
          <div className="section-heading">
            <h2>Contributors</h2>
          </div>
          <div className="contributor-list">
            {r.contributors.slice(0, 30).map((c, index) => (
              <span className="contributor" key={c.login || index}>
                {c.login || "Anonymous"} · {number(c.contributions)}
              </span>
            ))}
          </div>
        </>
      )}
    </>
  );
}
