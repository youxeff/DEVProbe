"use client";
import Link from "next/link";
import { useAuth } from "@/components/AuthProvider";
export default function LoginPage() {
  const { session } = useAuth();
  return (
    <div className="state-card">
      <h1>{session?.enabled ? "You are signed in." : "Local workspace"}</h1>
      <Link href="/">Open your workspace →</Link>
    </div>
  );
}
