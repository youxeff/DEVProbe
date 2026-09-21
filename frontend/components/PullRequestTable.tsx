import Link from "next/link";
import { GitPullRequest, ArrowUpRight } from "lucide-react";
import type { PullRequest } from "@/types";
import { date } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

export function PullRequestTable({
  pulls,
  repoId,
}: {
  pulls: PullRequest[];
  repoId: number;
}) {
  if (!pulls.length)
    return (
      <div className="empty-inline">
        <GitPullRequest size={28} />
        <h3>No open pull requests</h3>
        <p>
          Open a pull request on GitHub, then refresh to analyze its changes.
        </p>
      </div>
    );
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th>Pull request</th>
            <th>Author</th>
            <th>Status</th>
            <th>Updated</th>
            <th>
              <span className="sr-only">Open</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {pulls.map((pr) => (
            <tr key={pr.number}>
              <td>
                <Link
                  className="pr-title"
                  href={`/pull-requests/${repoId}/${pr.number}`}
                >
                  <GitPullRequest size={17} />
                  <span>
                    {pr.title}
                    <small>#{pr.number}</small>
                  </span>
                </Link>
              </td>
              <td>{pr.author || "Unknown"}</td>
              <td>
                <Badge variant="outline" className="status-open">
                  {pr.state}
                </Badge>
              </td>
              <td className="muted">{date(pr.updated_at)}</td>
              <td>
                <Link
                  href={`/pull-requests/${repoId}/${pr.number}`}
                  aria-label={`Open PR ${pr.number}`}
                >
                  <ArrowUpRight size={17} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
