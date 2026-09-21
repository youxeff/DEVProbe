import { Sparkles } from "lucide-react";
import type { Scan } from "@/types";
export function AIReviewCard({ scan }: { scan: Scan }) {
  const review = scan.ai_review;
  return (
    <section className="panel" style={{ marginTop: 22 }}>
      <div className="panel-heading">
        <h2>
          <Sparkles size={15} className="inline mr-2 text-primary" />
          AI review
        </h2>
        <span className="status-badge">
          {review
            ? "Generated explanation"
            : scan.ai_status === "failed"
              ? "Unavailable"
              : "Not enabled"}
        </span>
      </div>
      <div className="panel-body">
        {review ? (
          <>
            <p
              className="page-description"
              style={{ marginTop: 0, maxWidth: "none", marginBottom: 24 }}
            >
              {review.summary}
            </p>
            <div className="ai-grid">
              {[
                ["Main risks", review.risks],
                ["Suggested tests", review.suggested_tests],
                ["Recommended fixes", review.recommended_fixes],
              ].map(([title, items]) => (
                <div key={String(title)}>
                  <h3>{title}</h3>
                  <ul>
                    {(items as string[]).map((text, index) => (
                      <li key={index}>{text}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            <p className="form-hint" style={{ marginTop: 24 }}>
              AI-generated guidance · {review.model_name} · Verify
              recommendations against the code.
            </p>
          </>
        ) : (
          <p className="page-description" style={{ margin: 0 }}>
            {scan.ai_status === "failed"
              ? "AI review could not finish. Your analyzer findings and risk score are available above."
              : "AI review is disabled for this workspace. Analyzer findings and risk scoring are available."}
          </p>
        )}
      </div>
    </section>
  );
}
