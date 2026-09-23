"use client";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { Issue } from "@/types";
const colors: Record<string, string> = {
  critical: "#ba435c",
  high: "#dd8651",
  medium: "#e0b156",
  low: "#45a88f",
  info: "#84a8c2",
  security: "#338b80",
  complexity: "#73b3a8",
  style: "#9ccac0",
  testing: "#daa563",
  maintainability: "#89a5bf",
  documentation: "#becbd4",
};
export function IssueChart({
  issues,
  dimension,
}: {
  issues: Issue[];
  dimension: "severity" | "category";
}) {
  const keys =
    dimension === "severity"
      ? ["critical", "high", "medium", "low", "info"]
      : [
          "security",
          "complexity",
          "style",
          "testing",
          "maintainability",
          "documentation",
        ];
  const data = keys.map((name) => ({
    name,
    count: issues.filter((i) => i[dimension] === name).length,
  }));
  return (
    <div className="panel chart-panel">
      <h2>
        {dimension === "severity"
          ? "Severity breakdown"
          : "Findings by category"}
      </h2>
      {issues.length ? (
        <div
          role="img"
          aria-label={data.map((x) => `${x.name}: ${x.count}`).join(", ")}
        >
          <ResponsiveContainer width="100%" height={185}>
            <BarChart
              data={data}
              margin={{ left: -25, right: 4, top: 5, bottom: 0 }}
            >
              <XAxis
                dataKey="name"
                tick={{ fontSize: 9, fill: "#8297a3" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 9, fill: "#8297a3" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                cursor={{ fill: "#f4f7f8" }}
                contentStyle={{
                  borderRadius: 8,
                  fontSize: 12,
                  border: "1px solid #e4ecef",
                }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={35}>
                {data.map((x) => (
                  <Cell key={x.name} fill={colors[x.name]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="chart-empty">No findings to plot</div>
      )}
    </div>
  );
}
