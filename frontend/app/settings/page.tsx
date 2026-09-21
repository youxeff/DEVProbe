"use client";
import { useState } from "react";
import useSWR from "swr";
import {
  ArrowUpRight,
  GitBranch,
  Users,
  CreditCard,
  KeyRound,
  Building2,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { PageHeading } from "@/components/States";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Role } from "@/types/account";
import { date } from "@/lib/utils";

export default function SettingsPage() {
  const { session } = useAuth();
  const enabled = !!session?.enabled && !!session.user;
  const role = session?.active_organization?.role;
  const admin = role === "owner" || role === "admin";
  const usage = useSWR(enabled ? "usage" : null, api.usage);
  const members = useSWR(enabled ? "members" : null, api.members);
  const github = useSWR(enabled ? "github-settings" : null, api.githubSettings);
  const billing = useSWR(enabled ? "billing" : null, api.billing);
  const audit = useSWR(enabled && admin ? "audit" : null, api.audit);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [inviteUrl, setInviteUrl] = useState("");
  const [busy, setBusy] = useState(false);
  async function action(work: () => Promise<unknown>, success = "Saved.") {
    setError("");
    setMessage("");
    setBusy(true);
    try {
      await work();
      setMessage(success);
      await Promise.all([
        usage.mutate(),
        members.mutate(),
        github.mutate(),
        billing.mutate(),
        audit.mutate(),
      ]);
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "The action could not be completed.",
      );
    } finally {
      setBusy(false);
    }
  }
  if (!enabled)
    return (
      <>
        <PageHeading
          eyebrow="WORKSPACE SETTINGS"
          title="Your local workspace."
          description="Connect repositories and scan pull requests without an account in local development mode."
        />
        <section className="account-card">
          <h2>Team features</h2>
          <p className="muted">
            Accounts, invitations, GitHub App connections, and billing are
            available when the operator enables authentication.
          </p>
        </section>
      </>
    );
  const loadError =
    usage.error ||
    members.error ||
    github.error ||
    billing.error ||
    audit.error;
  return (
    <>
      <PageHeading
        eyebrow="WORKSPACE SETTINGS"
        title="Make DevProbe yours."
        description={`${session.active_organization?.name} · ${role}`}
        action={
          <Button
            variant="outline"
            disabled={busy}
            onClick={() =>
              action(async () => {
                await api.logout();
                localStorage.removeItem("devprobe-organization");
                window.location.assign("/");
              })
            }
          >
            Sign out
          </Button>
        }
      />
      {(error || loadError) && (
        <p role="alert" className="form-error account-notice">
          {error || loadError.message}
        </p>
      )}
      {message && (
        <p role="status" className="account-notice">
          {message}
        </p>
      )}
      <div className="two-column settings-grid">
        <section className="account-card">
          <div className="account-title">
            <CreditCard size={20} />
            <h2>Plan & usage</h2>
          </div>
          {usage.data && (
            <>
              <div className="plan-title">
                {usage.data.plan}
                <span>{usage.data.period}</span>
              </div>
              {(["scans", "repositories", "members"] as const).map((key) => (
                <div className="usage-row" key={key}>
                  <span>{key === "scans" ? "Monthly scans" : key}</span>
                  <strong>
                    {usage.data![key]} / {usage.data!.limits[key]}
                  </strong>
                  <progress
                    aria-label={`${key} usage`}
                    max={usage.data!.limits[key]}
                    value={usage.data![key]}
                  />
                </div>
              ))}
            </>
          )}
          <p className="muted">
            Accepted scans count toward the monthly limit, including scans that
            later fail.
          </p>
          {billing.data?.configured ? (
            <div className="account-actions">
              {role === "owner" && usage.data?.plan === "free" && (
                <Button
                  disabled={busy}
                  onClick={() =>
                    action(async () => {
                      window.location.assign((await api.checkout()).url);
                    }, "Opening checkout…")
                  }
                >
                  Upgrade to Pro <ArrowUpRight size={14} />
                </Button>
              )}
              {role === "owner" && billing.data.has_customer && (
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={() =>
                    action(async () => {
                      window.location.assign((await api.billingPortal()).url);
                    }, "Opening billing…")
                  }
                >
                  Manage billing
                </Button>
              )}
              {role !== "owner" && (
                <p className="muted">
                  Your organization owner manages billing.
                </p>
              )}
            </div>
          ) : (
            <p className="muted">
              Paid plans are not enabled for this deployment.
            </p>
          )}
        </section>
        <section className="account-card">
          <div className="account-title">
            <GitBranch size={20} />
            <h2>GitHub connection</h2>
          </div>
          <p className="muted">
            Install DevProbe on selected repositories, then verify your account
            to link the installation.
          </p>
          {github.data?.configured ? (
            <>
              {github.data.install_url && admin && (
                <a
                  className="inline-link"
                  href={github.data.install_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Install the GitHub App <ArrowUpRight size={14} />
                </a>
              )}
              {admin && (
                <form
                  className="account-form"
                  onSubmit={(event) => {
                    event.preventDefault();
                    const data = new FormData(event.currentTarget);
                    void action(async () => {
                      window.location.assign(
                        (
                          await api.connectInstallation(
                            Number(data.get("installation")),
                          )
                        ).url,
                      );
                    }, "Opening GitHub…");
                  }}
                >
                  <label>
                    Installation ID
                    <Input
                      name="installation"
                      type="number"
                      min={1}
                      required
                      placeholder="From your GitHub installation settings"
                    />
                  </label>
                  <Button disabled={busy}>Verify and connect</Button>
                </form>
              )}
            </>
          ) : (
            <p className="muted">
              The operator has not configured a GitHub App yet. Public
              repository scans remain available.
            </p>
          )}
          {github.data?.installations.map((item) => (
            <div className="installation-row" key={item.id}>
              <strong>{item.account_login}</strong>
              <span className="muted">
                {item.active ? "Connected" : "Disconnected"}
              </span>
              {admin && (
                <>
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={item.publish_checks}
                      disabled={busy || !item.active}
                      onChange={(event) =>
                        action(() =>
                          api.updateInstallation(item.id, event.target.checked),
                        )
                      }
                    />{" "}
                    Publish Checks after scans
                  </label>
                  {item.active && (
                    <button
                      className="text-action"
                      disabled={busy}
                      onClick={() =>
                        action(() => api.disconnectInstallation(item.id))
                      }
                    >
                      Disconnect
                    </button>
                  )}
                </>
              )}
            </div>
          ))}
        </section>
      </div>
      <section className="account-card">
        <div className="account-title">
          <Users size={20} />
          <h2>People & access</h2>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Member</th>
                <th>Email</th>
                <th>Role</th>
                {admin && <th>Action</th>}
              </tr>
            </thead>
            <tbody>
              {members.data?.map((member) => (
                <tr key={member.id}>
                  <td>
                    <strong>{member.name}</strong>
                  </td>
                  <td>{member.email}</td>
                  <td>
                    {admin && (role === "owner" || member.role !== "owner") ? (
                      <select
                        aria-label={`Role for ${member.email}`}
                        value={member.role}
                        disabled={busy}
                        onChange={(event) =>
                          action(() =>
                            api.changeMember(
                              member.id,
                              event.target.value as Role,
                            ),
                          )
                        }
                      >
                        {(role === "owner"
                          ? ["owner", "admin", "member", "viewer"]
                          : ["admin", "member", "viewer"]
                        ).map((value) => (
                          <option key={value} value={value}>
                            {value}
                          </option>
                        ))}
                      </select>
                    ) : (
                      member.role
                    )}
                  </td>
                  {admin && (
                    <td>
                      {(role === "owner" || member.role !== "owner") && (
                        <button
                          className="text-action"
                          disabled={busy}
                          onClick={() =>
                            action(() => api.removeMember(member.id))
                          }
                        >
                          Remove
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {admin && (
          <form
            className="account-form invite-form"
            onSubmit={(event) => {
              event.preventDefault();
              const data = new FormData(event.currentTarget);
              void action(async () => {
                const invitation = await api.invite(
                  String(data.get("email")),
                  String(data.get("role")) as Exclude<Role, "owner">,
                );
                setInviteUrl(invitation.invite_url);
              }, "Invitation ready. Share the link with the intended recipient.");
            }}
          >
            <label>
              Email
              <Input
                name="email"
                type="email"
                required
                placeholder="teammate@example.com"
              />
            </label>
            <label>
              Role
              <select name="role" defaultValue="member">
                <option value="member">Member</option>
                <option value="viewer">Viewer</option>
                <option value="admin">Admin</option>
              </select>
            </label>
            <Button disabled={busy}>Create invitation</Button>
          </form>
        )}
        {inviteUrl && (
          <label className="account-form">
            Invitation link — expires in 48 hours
            <Input
              value={inviteUrl}
              readOnly
              onFocus={(event) => event.currentTarget.select()}
            />
          </label>
        )}
      </section>
      <div className="two-column settings-grid">
        <section className="account-card">
          <div className="account-title">
            <Building2 size={20} />
            <h2>Another organization</h2>
          </div>
          <p className="muted">
            Create a separate workspace with its own repositories, members, and
            scan history.
          </p>
          <form
            className="account-form"
            onSubmit={(event) => {
              event.preventDefault();
              const data = new FormData(event.currentTarget);
              void action(async () => {
                const org = await api.createOrganization(
                  String(data.get("organization")),
                );
                localStorage.setItem("devprobe-organization", String(org.id));
                window.location.assign("/");
              });
            }}
          >
            <label>
              New organization name
              <Input name="organization" required maxLength={100} />
            </label>
            <Button variant="outline" disabled={busy}>
              Create organization
            </Button>
          </form>
        </section>
        <section className="account-card">
          <div className="account-title">
            <KeyRound size={20} />
            <h2>Account security</h2>
          </div>
          <p className="muted">
            Changing your password signs out all sessions.
          </p>
          <form
            className="account-form"
            onSubmit={(event) => {
              event.preventDefault();
              const data = new FormData(event.currentTarget);
              void action(async () => {
                await api.changePassword(
                  String(data.get("current")),
                  String(data.get("new")),
                );
                localStorage.removeItem("devprobe-organization");
                window.location.assign("/login");
              });
            }}
          >
            <label>
              Current password
              <Input
                name="current"
                type="password"
                minLength={12}
                maxLength={128}
                required
                autoComplete="current-password"
              />
            </label>
            <label>
              New password
              <Input
                name="new"
                type="password"
                minLength={12}
                maxLength={128}
                required
                autoComplete="new-password"
              />
            </label>
            <Button variant="outline" disabled={busy}>
              Change password
            </Button>
          </form>
        </section>
      </div>
      {admin && (
        <section className="account-card">
          <h2>Recent audit activity</h2>
          <p className="muted">The latest 100 organization events.</p>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Action</th>
                  <th>Actor</th>
                  <th>Resource</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {audit.data?.map((event) => (
                  <tr key={event.id}>
                    <td>{event.action.replaceAll(".", " · ")}</td>
                    <td>
                      {event.user_id ? `User #${event.user_id}` : "System"}
                    </td>
                    <td>{event.resource_id ?? "—"}</td>
                    <td>{date(event.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}
