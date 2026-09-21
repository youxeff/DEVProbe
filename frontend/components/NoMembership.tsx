"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
export function NoMembership() {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <section className="account-card auth-card">
      <h1>Choose a new workspace</h1>
      <p className="muted">
        You no longer belong to an organization. Open an invitation link from
        your administrator, or create your own workspace.
      </p>
      <form
        className="account-form"
        onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          setError("");
          const data = new FormData(event.currentTarget);
          try {
            const org = await api.createOrganization(String(data.get("name")));
            localStorage.setItem("devprobe-organization", String(org.id));
            window.location.assign("/");
          } catch (error) {
            setError(
              error instanceof Error
                ? error.message
                : "Unable to create organization.",
            );
            setBusy(false);
          }
        }}
      >
        <label>
          Organization name
          <Input name="name" required maxLength={100} />
        </label>
        <Button disabled={busy}>Create organization</Button>
      </form>
      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}
    </section>
  );
}
