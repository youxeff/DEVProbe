"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/AuthProvider";
export default function InvitePage() {
  const { session } = useAuth();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function accept() {
    setBusy(true);
    setError("");
    try {
      const result = await api.acceptInvitation(window.location.hash.slice(1));
      localStorage.setItem(
        "devprobe-organization",
        String(result.organization_id),
      );
      window.location.replace("/settings");
    } catch (error) {
      setError(
        error instanceof Error ? error.message : "Unable to accept invitation.",
      );
      setBusy(false);
    }
  }
  return (
    <section className="account-card auth-card">
      <h1>Join your team</h1>
      <p className="muted">
        Accept this invitation as {session?.user?.email}. Use the email address
        your administrator invited.
      </p>
      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}
      <Button onClick={accept} disabled={busy || !session?.user}>
        {busy ? "Joining…" : "Accept invitation"}
      </Button>
    </section>
  );
}
