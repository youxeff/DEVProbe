"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, GitBranch, LoaderCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";

export function RepoForm() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const parsed = new URL(url);
      if (
        parsed.hostname !== "github.com" ||
        parsed.pathname.split("/").filter(Boolean).length < 2
      )
        throw Error();
    } catch {
      setError(
        "Enter a GitHub repository URL, such as https://github.com/owner/repository.",
      );
      return;
    }
    setBusy(true);
    try {
      const repo = await api.connect(url.trim());
      router.push(`/repositories/${repo.id}`);
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not connect the repository.",
      );
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit} className="repo-form">
      <label htmlFor="repo-url">GitHub repository URL</label>
      <div className="repo-form-row">
        <div className="repo-input-wrap">
          <GitBranch size={20} />
          <Input
            id="repo-url"
            placeholder="https://github.com/owner/repository"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={busy}
            autoComplete="url"
            aria-describedby={error ? "repo-error" : undefined}
          />
        </div>
        <Button type="submit" size="lg" disabled={busy || !url.trim()}>
          {busy ? (
            <>
              <LoaderCircle size={16} className="spin" /> Connecting…
            </>
          ) : (
            <>
              Analyze repository <ArrowRight size={16} />
            </>
          )}
        </Button>
      </div>
      {error && (
        <p id="repo-error" className="form-error" role="alert">
          {error}
        </p>
      )}
      <p className="form-hint">
        Connect a repository to browse pull requests and start a review.
      </p>
    </form>
  );
}
