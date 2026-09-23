import { ShieldCheck } from "lucide-react";
import type { Scan } from "@/types";
export function RiskScoreCard({ scan }: { scan: Scan }) {
  return (
    <div className="panel risk-card">
      <div className="risk-label">
        <ShieldCheck size={16} /> Pull request risk
      </div>
      <div className="risk-value">{scan.risk_score ?? "—"}</div>
      {scan.risk_level && (
        <span className={`risk-badge risk-${scan.risk_level.toLowerCase()}`}>
          {scan.risk_level} risk
        </span>
      )}
      <p className="risk-caption">
        Deterministic score · uncapped · scoring v1
      </p>
    </div>
  );
}
