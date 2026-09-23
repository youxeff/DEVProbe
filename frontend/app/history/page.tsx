"use client";
import { useState } from "react";
import useSWR from "swr";
import {
  Activity,
  Bug,
  Clock3,
  ScanLine,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { api } from "@/lib/api";
import { number, duration } from "@/lib/utils";
import { PageHeading, LoadingState, ErrorState } from "@/components/States";
import { StatCard } from "@/components/Stats";
import { TrendChart } from "@/components/TrendChart";
import { ScanHistoryTable } from "@/components/ScanHistoryTable";
import { Button } from "@/components/ui/button";
export default function History() {
  const [offset, setOffset] = useState(0);
  const { data: summary, error } = useSWR("analytics", api.analytics);
  const { data: page, error: pageError } = useSWR(["history", offset], () =>
    api.scans(offset),
  );
  if (error || pageError) return <ErrorState error={error || pageError} />;
  if (!summary || !page) return <LoadingState label="Loading scan history…" />;
  return (
    <>
      <PageHeading
        eyebrow="Quality over time"
        title="Every scan tells a story."
        description="Compare results across your workspace and see where review effort is going."
      />
      <div className="stats-grid">
        <StatCard
          label="Total scans"
          value={number(summary.total_scans)}
          detail={`${summary.completed_scans} completed · ${summary.failed_scans} failed`}
          icon={ScanLine}
        />
        <StatCard
          label="Average risk score"
          value={summary.average_risk_score?.toFixed(1) ?? "—"}
          detail="Completed scans only"
          icon={Activity}
        />
        <StatCard
          label="Total findings"
          value={number(summary.total_issues)}
          detail={`${number(summary.files_analyzed)} files analyzed`}
          icon={Bug}
        />
        <StatCard
          label="Average duration"
          value={duration(summary.average_duration_seconds)}
          detail="Completed scans only"
          icon={Clock3}
        />
      </div>
      <div className="two-column">
        <TrendChart trend={summary.trend} metric="risk_score" />
        <TrendChart trend={summary.trend} metric="total_issues" />
      </div>
      <p className="form-hint" style={{ marginTop: 12 }}>
        Trends show the latest 30 completed scans. Scores use the same uncapped
        scoring formula.
      </p>
      <div className="section-heading">
        <h2>Scan history</h2>
        <span className="muted">{page.total} scans</span>
      </div>
      <div className="panel">
        <ScanHistoryTable scans={page.items} />
      </div>
      <div className="section-heading">
        <p>
          {page.total
            ? `${offset + 1}–${Math.min(offset + 25, page.total)} of ${page.total}`
            : "No scans yet"}
        </p>
        <div className="inline-meta">
          <Button
            variant="outline"
            size="sm"
            disabled={!offset}
            onClick={() => setOffset(offset - 25)}
          >
            <ChevronLeft size={14} />
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={offset + 25 >= page.total}
            onClick={() => setOffset(offset + 25)}
          >
            Next
            <ChevronRight size={14} />
          </Button>
        </div>
      </div>
    </>
  );
}
