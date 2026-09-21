"use client";
import useSWR from "swr";
import { api } from "@/lib/api";
import { RepoForm } from "@/components/RepoForm";
import { RepositoryCard } from "@/components/RepositoryCard";
import { PageHeading, LoadingState, ErrorState } from "@/components/States";
export default function Repositories() {
  const { data, error, mutate } = useSWR("repositories", api.repositories);
  return (
    <>
      <PageHeading
        eyebrow="Codebase directory"
        title="Repositories"
        description="Connect a repository and put your next pull request in focus."
      />
      <div className="panel panel-body">
        <RepoForm />
      </div>
      <div className="section-heading">
        <h2>Connected repositories</h2>
      </div>
      {error ? (
        <ErrorState error={error} retry={() => mutate()} />
      ) : !data ? (
        <LoadingState />
      ) : data.length ? (
        <div className="repo-grid">
          {data.map((repo) => (
            <RepositoryCard key={repo.id} repo={repo} />
          ))}
        </div>
      ) : (
        <div className="empty-state">
          Your connected repositories will appear here.
        </div>
      )}
    </>
  );
}
