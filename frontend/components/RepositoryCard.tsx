import Link from "next/link";
import { ArrowUpRight, GitFork, GitBranch, Star } from "lucide-react";
import type { Repository } from "@/types";
import { number } from "@/lib/utils";
import { Card } from "@/components/ui/card";

export function RepositoryCard({ repo }: { repo: Repository }) {
  return (
    <Link href={`/repositories/${repo.id}`} className="repo-card-link">
      <Card className="repo-card">
        <div className="row-between">
          <span className="repo-icon">
            <GitBranch size={21} />
          </span>
          <ArrowUpRight size={18} />
        </div>
        <h3>{repo.full_name}</h3>
        <p>{repo.description || "No description provided."}</p>
        <div className="repo-card-meta">
          <span>
            <i className="language-dot" />
            {repo.language || "Mixed"}
          </span>
          <span>
            <Star size={14} />
            {number(repo.stars)}
          </span>
          <span>
            <GitFork size={14} />
            {number(repo.forks)}
          </span>
        </div>
      </Card>
    </Link>
  );
}
