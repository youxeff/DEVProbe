"use client";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { Analytics } from "@/types";
export function TrendChart({
  trend,
  metric,
}: {
  trend: Analytics["trend"];
  metric: "risk_score" | "total_issues";
}) {
  return (
    <div className="panel chart-panel">
      <h2>
        {metric === "risk_score"
          ? "Risk score over time"
          : "Findings over time"}
      </h2>
      {trend.length ? (
        <div
          role="img"
          aria-label={`${trend.length} completed scans, ${metric.replaceAll("_", " ")}`}
        >
          <ResponsiveContainer width="100%" height={220}>
            <LineChart
              data={trend.map((p) => ({ ...p, label: `#${p.scan_id}` }))}
              margin={{ left: -20, right: 15, top: 15 }}
            >
              <CartesianGrid
                strokeDasharray="3 5"
                vertical={false}
                stroke="#e9eef1"
              />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 10, fill: "#8297a3" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 10, fill: "#8297a3" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
              <Line
                name={metric === "risk_score" ? "Risk score" : "Findings"}
                dataKey={metric}
                stroke={metric === "risk_score" ? "#178d7b" : "#cc9554"}
                strokeWidth={2}
                dot={{ r: 3 }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="chart-empty">Run a scan to start your history.</div>
      )}
    </div>
  );
}
