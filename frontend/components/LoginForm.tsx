"use client";
import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "./AuthProvider";

export function LoginForm() {
  const { session, refresh } = useAuth();
  const [register, setRegister] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    const credentials = {
      email: String(data.get("email")),
      password: String(data.get("password")),
    };
    try {
      if (register)
        await api.register({
          ...credentials,
          name: String(data.get("name")),
          organization_name: String(data.get("organization")),
        });
      else await api.login(credentials);
      localStorage.removeItem("devprobe-organization");
      await refresh();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to sign in.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="account-card auth-card">
      <span className="brand-symbol">
        <ShieldCheck />
      </span>
      <p className="eyebrow">YOUR CODE. YOUR WORKSPACE.</p>
      <h1>{register ? "Create your workspace" : "Welcome to DevProbe"}</h1>
      <p className="muted">Sign in to review pull requests with your team.</p>
      <form onSubmit={submit} className="account-form">
        {register && (
          <>
            <label>
              Your name
              <Input name="name" required maxLength={100} autoComplete="name" />
            </label>
            <label>
              Organization name
              <Input
                name="organization"
                required
                maxLength={100}
                autoComplete="organization"
              />
            </label>
          </>
        )}
        <label>
          Email
          <Input name="email" type="email" required autoComplete="email" />
        </label>
        <label>
          Password
          <Input
            name="password"
            type="password"
            required
            minLength={12}
            maxLength={128}
            autoComplete={register ? "new-password" : "current-password"}
          />
        </label>
        <small className="muted">Use at least 12 characters.</small>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <Button disabled={busy} type="submit">
          {busy ? "Please wait…" : register ? "Create account" : "Sign in"}
        </Button>
      </form>
      {session?.registration_enabled && (
        <button
          className="text-action"
          onClick={() => {
            setRegister(!register);
            setError("");
          }}
        >
          {register
            ? "Already have an account? Sign in"
            : "New here? Create an account"}
        </button>
      )}
    </section>
  );
}
