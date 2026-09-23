"use client";
import { useState } from "react";
import type { Issue } from "@/types";
const filterKeys = ["severity", "category", "file_path", "tool"] as const;
const labels = {
  severity: "Severity",
  category: "Category",
  file_path: "File",
  tool: "Tool",
};
export function IssueTable({ issues }: { issues: Issue[] }) {
  const [filters, setFilters] = useState({
    severity: "",
    category: "",
    file_path: "",
    tool: "",
  });
  const filtered = issues.filter((issue) =>
    filterKeys.every((key) => !filters[key] || issue[key] === filters[key]),
  );
  return (
    <div className="panel">
      <div className="filters">
        {filterKeys.map((key) => (
          <label key={key}>
            {labels[key]}
            <select
                aria-label={labels[key]}
              value={filters[key]}
              onChange={(e) =>
                setFilters({ ...filters, [key]: e.target.value })
              }
            >
              <option value="">All {labels[key].toLowerCase()}s</option>
              {[...new Set(issues.map((issue) => issue[key]))]
                .sort()
                .map((value) => (
                  <option key={value}>{value}</option>
                ))}
            </select>
          </label>
        ))}
      </div>
      {filtered.length ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                {[
                  "Severity",
                  "Category / tool",
                  "Location",
                  "Finding & recommendation",
                ].map((x) => (
                  <th key={x}>{x}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((issue, index) => (
                <tr
                  key={`${issue.file_path}-${issue.line_number}-${issue.rule_id}-${index}`}
                >
                  <td>
                    <span className={`risk-badge risk-${issue.severity}`}>
                      {issue.severity}
                    </span>
                  </td>
                  <td>
                    {issue.category}
                    <p className="pr-number">{issue.tool}</p>
                  </td>
                  <td className="mono">
                    {issue.file_path}
                    {issue.line_number && (
                      <p className="pr-number">Line {issue.line_number}</p>
                    )}
                  </td>
                  <td className="issue-description">
                    {issue.message}
                    <p>{issue.recommendation}</p>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          {issues.length
            ? "No findings match these filters."
            : "No findings from the enabled checks. Human review is still recommended."}
        </div>
      )}
    </div>
  );
}
