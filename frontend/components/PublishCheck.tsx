"use client";
import { useState } from "react";
import { GitBranch } from "lucide-react";
import { useAuth } from "./AuthProvider";
import { Button } from "./ui/button";
import { api } from "@/lib/api";
export function PublishCheck({ scanId }: { scanId: number }) {
  const { session } = useAuth();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  if (!session?.enabled || session.active_organization?.role === "viewer")
    return null;
  return (
    <div className="publish-check">
      <Button
        variant="outline"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          setMessage("");
          try {
            await api.publishCheck(scanId);
            setMessage(
              "GitHub Check published. Repeated publication updates the existing Check.",
            );
          } catch (error) {
            setMessage(
              error instanceof Error ? error.message : "Unable to publish.",
            );
          } finally {
            setBusy(false);
          }
        }}
      >
        <GitBranch size={16} />
        {busy ? "Publishing…" : "Publish GitHub Check"}
      </Button>
      {message && <p role="status">{message}</p>}
    </div>
  );
}
