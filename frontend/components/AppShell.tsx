"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import useSWR from "swr";
import {
  Activity,
  ChartNoAxesCombined,
  ArrowUpRight,
  Blocks,
  BookOpen,
  FolderGit2,
  LayoutDashboard,
  ShieldCheck,
  Settings,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useAuth } from "./AuthProvider";

const navigation = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/repositories", label: "Repositories", icon: FolderGit2 },
  { href: "/history", label: "Scan history", icon: ChartNoAxesCombined },
  { href: "/architecture", label: "How it works", icon: Blocks },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { session } = useAuth();
  const pathname = usePathname();
  const { data } = useSWR("health", api.health, {
    refreshInterval: 30000,
    shouldRetryOnError: false,
  });
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link href="/" className="brand">
          <span className="brand-symbol">
            <Activity size={23} />
          </span>
          DevProbe<span className="brand-dot">.</span>
        </Link>
        <div className="workspace-label">YOUR WORKSPACE</div>
        <nav aria-label="Main navigation">
          {navigation.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "nav-link",
                (href === "/"
                  ? pathname === href
                  : pathname.startsWith(href)) && "active",
              )}
            >
              <Icon size={18} />
              {label}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <ShieldCheck size={23} />
          <p>
            Better code.
            <br />
            <strong>Before the merge.</strong>
          </p>
          <a
            href="https://github.com/youxeff/DEVProbe"
            target="_blank"
            rel="noreferrer"
          >
            View project <ArrowUpRight size={14} />
          </a>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            <span className="muted">Workspace</span>
            <span className="breadcrumb-slash">/</span>
            {session?.enabled && session.user ? (
              <select
                className="organization-select"
                aria-label="Active organization"
                value={session.active_organization?.id ?? ""}
                onChange={(event) => {
                  localStorage.setItem(
                    "devprobe-organization",
                    event.target.value,
                  );
                  window.location.assign("/");
                }}
              >
                {session.organizations.map((org) => (
                  <option key={org.id} value={org.id}>
                    {org.name}
                  </option>
                ))}
              </select>
            ) : (
              <span>Code quality</span>
            )}
          </div>
          <div className="topbar-right">
            <span
              className={cn("connection", data?.status === "ok" && "online")}
            >
              <i />
              {data?.status === "ok" ? "API connected" : "Connecting"}
            </span>
            <Link href="/architecture" aria-label="Documentation">
              <BookOpen size={18} />
            </Link>
            <Link
              className="avatar"
              href="/settings"
              aria-label="Account settings"
            >
              {session?.user?.name.slice(0, 2).toUpperCase() ?? "DP"}
            </Link>
          </div>
        </header>
        <main className="main-content">{children}</main>
        <footer className="footer">
          DevProbe <span>Built for thoughtful code review.</span>
        </footer>
      </div>
    </div>
  );
}
