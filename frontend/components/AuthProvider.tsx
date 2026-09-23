"use client";
import { createContext, useContext, useEffect } from "react";
import useSWR from "swr";
import { api, ApiError } from "@/lib/api";
import type { AuthSession } from "@/types/account";
import { ErrorState, LoadingState } from "./States";
import { LoginForm } from "./LoginForm";
import { NoMembership } from "./NoMembership";
import { usePathname } from "next/navigation";

const AuthContext = createContext<{
  session?: AuthSession;
  error?: Error;
  refresh: () => Promise<unknown>;
}>({ refresh: async () => {} });

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { data, error, mutate } = useSWR("auth-session", api.session, {
    refreshInterval: 60000,
    shouldRetryOnError: false,
  });
  useEffect(() => {
    const changed = (event: StorageEvent) => {
      if (event.key === "devprobe-organization") window.location.assign("/");
    };
    window.addEventListener("storage", changed);
    return () => window.removeEventListener("storage", changed);
  }, []);
  return (
    <AuthContext.Provider value={{ session: data, error, refresh: mutate }}>
      {children}
    </AuthContext.Provider>
  );
}
export const useAuth = () => useContext(AuthContext);

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { session, error, refresh } = useAuth();
  const pathname = usePathname();
  if (error)
    return (
      <ErrorState
        error={error}
        retry={() => {
          if (error instanceof ApiError && error.status === 404)
            localStorage.removeItem("devprobe-organization");
          void refresh();
        }}
      />
    );
  if (!session) return <LoadingState />;
  if (session.enabled && !session.user) return <LoginForm />;
  if (session.enabled && !session.active_organization && pathname !== "/invite")
    return <NoMembership />;
  return children;
}
