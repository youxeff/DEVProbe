"use client";
import Link from "next/link";
import useSWR from "swr";
import {
  ArrowRight,
  GitPullRequest,
  ScanLine,
  ShieldCheck,
} from "lucide-react";
import { RepoForm } from "@/components/RepoForm";
import { RepositoryCard } from "@/components/RepositoryCard";
import { PageHeading, ErrorState } from "@/components/States";
import { api } from "@/lib/api";
export default function Home() {
  const { data, error, mutate } = useSWR("repositories", api.repositories, {
    shouldRetryOnError: false,
  });
  return (
    <>
      <PageHeading
        eyebrow="Your code, with confidence"
        title="Good reviews start here."
        description="Turn pull request changes into a clear picture of risk, quality, and what to review next."
      />
      <section className="hero-panel">
        <div className="hero-main">
          <div className="hero-icon">
            <ScanLine size={23} />
          </div>
          <h2>Take a closer look at your code.</h2>
          <p>
            Connect a GitHub repository to explore pull requests and run your
            first DevProbe scan.
          </p>
          <RepoForm />
        </div>
        <div className="hero-aside">
          {[
            ["Connect your repository", "Start with a GitHub repository URL."],
            [
              "Choose a pull request",
              "See exactly what changed before you scan.",
            ],
            [
              "Review with confidence",
              "Explore findings and a consistent risk score.",
            ],
          ].map(([title, description], index) => (
            <div className="step" key={title}>
              <span className="step-number">0{index + 1}</span>
              <div>
                <h3>{title}</h3>
                <p>{description}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
      <div className="section-heading">
        <div>
          <h2>Your repositories</h2>
          <p>Pick up where your next review begins.</p>
        </div>
        <Link href="/repositories">
          View all <ArrowRight size={12} className="inline" />
        </Link>
      </div>
      {error ? (
        <ErrorState error={error} retry={() => mutate()} />
      ) : data?.length ? (
        <div className="repo-grid">
          {data.slice(0, 6).map((repo) => (
            <RepositoryCard key={repo.id} repo={repo} />
          ))}
        </div>
      ) : (
        <div className="empty-state">
          {data
            ? "No repositories connected yet. Add your first repository above."
            : "Loading repositories…"}
        </div>
      )}
      <div className="section-heading">
        <h2>A little more clarity. Every merge.</h2>
      </div>
      <div className="feature-grid">
        {[
          {
            icon: GitPullRequest,
            title: "Changes in context",
            text: "Browse pull requests and their changed files in one focused workspace.",
          },
          {
            icon: ShieldCheck,
            title: "Signals you can inspect",
            text: "Every finding includes its source, severity, location, and a recommended next step.",
          },
          {
            icon: ScanLine,
            title: "Consistent risk scoring",
            text: "A transparent formula helps you compare changes without relying on an AI opinion.",
          },
        ].map(({ icon: Icon, title, text }) => (
          <div key={title} className="panel feature-card">
            <Icon size={21} />
            <h3>{title}</h3>
            <p>{text}</p>
          </div>
        ))}
      </div>
    </>
  );
}
