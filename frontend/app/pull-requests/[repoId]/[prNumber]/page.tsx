"use client";
import { use, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import useSWR from "swr";
import {
  ArrowLeft,
  FileCode,
  Plus,
  Minus,
  ScanLine,
  LoaderCircle,
  GitCompareArrows,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { number } from "@/lib/utils";
import { PageHeading, LoadingState, ErrorState } from "@/components/States";
import { StatCard } from "@/components/Stats";
import { ChangedFilesList } from "@/components/ChangedFilesList";
import { Button } from "@/components/ui/button";
export default function PullPage({
  params,
}: {
  params: Promise<{ repoId: string; prNumber: string }>;
}) {
  const { repoId, prNumber } = use(params);
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [scanError, setScanError] = useState("");
  const { data, error, mutate } = useSWR(
    ["pull", repoId, prNumber],
    async () => {
      const repo = await api.repository(repoId);
      const [pull, changed] = await Promise.all([
        api.pull(repo.html_url, Number(prNumber)),
        api.files(repo.html_url, Number(prNumber)),
      ]);
      return { repo, pull, files: changed.files };
    },
  );
  if (error) return <ErrorState error={error} retry={() => mutate()} />;
  if (!data) return <LoadingState label="Fetching pull request changes…" />;
  const { repo, pull, files } = data;
  const additions = files.reduce((n, f) => n + f.additions, 0),
    deletions = files.reduce((n, f) => n + f.deletions, 0);
  async function analyze() {
    setBusy(true);
    setScanError("");
    try {
      const result = await api.createScan(repo.html_url, Number(prNumber));
      router.push(`/scans/${result.scan_id}`);
    } catch (e) {
      if (e instanceof ApiError && e.scanId) router.push(`/scans/${e.scanId}`);
      else
        setScanError(e instanceof Error ? e.message : "Scan could not start.");
      setBusy(false);
    }
  }
  return (
    <>
      <Link className="back-link" href={`/repositories/${repoId}`}>
        <ArrowLeft size={13} />
        {repo.full_name}
      </Link>
      <PageHeading
        eyebrow={`Pull request #${pull.number}`}
        title={pull.title}
        description={`Opened by ${pull.author || "an unknown author"}. Review the changed files, then run an analysis.`}
        action={
          <Button size="lg" onClick={analyze} disabled={busy}>
            {busy ? (
              <LoaderCircle className="spin" size={16} />
            ) : (
              <ScanLine size={16} />
            )}{" "}
            {busy ? "Analyzing PR…" : "Analyze PR"}
          </Button>
        }
      />
      <div className="inline-meta">
        <span className={`status-badge status-${pull.state}`}>
          {pull.state}
        </span>
        <a href={pull.html_url} target="_blank" rel="noreferrer">
          View pull request on GitHub ↗
        </a>
      </div>
      {scanError && (
        <p role="alert" className="alert-inline">
          {scanError}
        </p>
      )}
      <div className="stats-grid">
        <StatCard
          label="Changed files"
          value={number(files.length)}
          icon={FileCode}
        />
        <StatCard
          label="Additions"
          value={`+${number(additions)}`}
          icon={Plus}
        />
        <StatCard
          label="Deletions"
          value={`−${number(deletions)}`}
          icon={Minus}
        />
        <StatCard
          label="Changed lines"
          value={number(additions + deletions)}
          icon={GitCompareArrows}
        />
      </div>
      <div className="section-heading">
        <div>
          <h2>Changed files</h2>
          <p>The scope of this pull request.</p>
        </div>
      </div>
      <div className="panel">
        <ChangedFilesList files={files} />
      </div>
      <p className="analysis-note">
        DevProbe analyzes changes without running your repository’s application
        or test scripts. Findings help focus a human review.
      </p>
    </>
  );
}
