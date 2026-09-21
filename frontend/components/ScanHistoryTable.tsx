import Link from "next/link";
import { date, duration, number } from "@/lib/utils";
import type { Scan } from "@/types";
export function ScanHistoryTable({ scans }: { scans: Scan[] }) {
  return scans.length ? (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {[
              "Scan",
              "Pull request",
              "Status",
              "Risk",
              "Issues",
              "Duration",
              "Created",
            ].map((x) => (
              <th key={x}>{x}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {scans.map((scan) => (
            <tr key={scan.id}>
              <td>
                <Link className="pr-title" href={`/scans/${scan.id}`}>
                  Scan #{scan.id}
                </Link>
              </td>
              <td>#{scan.pr_number}</td>
              <td>
                <span className={`status-badge status-${scan.status}`}>
                  {scan.status}
                </span>
              </td>
              <td>
                {scan.risk_level ? (
                  <span
                    className={`risk-badge risk-${scan.risk_level.toLowerCase()}`}
                  >
                    {scan.risk_score} · {scan.risk_level}
                  </span>
                ) : (
                  "—"
                )}
              </td>
              <td>{number(scan.total_issues)}</td>
              <td>{duration(scan.scan_duration_seconds)}</td>
              <td>{date(scan.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <div className="empty-state">
      No scans yet. Open a pull request to run your first analysis.
    </div>
  );
}
