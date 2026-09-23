import { PageHeading } from "@/components/States";
export default function Architecture() {
  return (
    <>
      <PageHeading
        eyebrow="Under the hood"
        title="Built for a thoughtful review."
        description="Understand what a scan measures, where its signals come from, and how to use them."
      />
      <div className="panel prose-panel">
        <h2>From change to finding</h2>
        <p>
          DevProbe retrieves a pull request and its changed files from GitHub.
          The scan service coordinates analyzers, normalizes their findings, and
          calculates a deterministic risk score. Results are stored so you can
          return to a review later.
        </p>
        <h2>A score you can explain</h2>
        <p>
          Security findings add 3–15 points depending on severity. Complexity
          adds 3–5 points. Style findings and large file changes add 2 points
          each, and a missing-test warning adds 4. Large pull requests add 10
          points for more than 15 files, plus 10 points for 501–1000 changed
          lines or 20 for more than 1000.
        </p>
        <p>
          Low: 0–20 · Medium: 21–50 · High: 51–80 · Critical: 81+. The score is
          uncapped. It is a review prioritization signal, not a probability of
          failure.
        </p>
        <h2>Privacy and boundaries</h2>
        <p>
          Credentials stay on the server. Full patches are used during analysis
          and are not retained in scan results. The basic analyzer reads added
          lines; missing or truncated patches limit what it can inspect. A
          potential secret finding is a heuristic, and a missing-test warning
          does not prove that coverage is absent.
        </p>
        <p>
          DevProbe does not run repository applications, build hooks, or test
          suites in the API process. Human review remains part of every merge
          decision.
        </p>
      </div>
    </>
  );
}
