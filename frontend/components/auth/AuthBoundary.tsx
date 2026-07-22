"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { BookOpenCheck } from "lucide-react";
import { API_BASE } from "@/lib/api";
import type { AuthUser } from "@/lib/auth/types";

const PUBLIC_PATHS = ["/onboarding", "/auth", "/auth/callback", "/auth-diagnostics", "/privacy", "/terms"];
const AuthContext = createContext<{ user: AuthUser | null; refresh: () => Promise<void> }>({ user: null, refresh: async () => undefined });

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthBoundary({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [checking, setChecking] = useState(true);
  const isPublic = PUBLIC_PATHS.some((item) => path === item || path.startsWith(`${item}/`));

  async function loadUser() {
    let response = await fetch(`${API_BASE}/auth/me`, { credentials: "include", cache: "no-store" });
    if (response.status === 401) {
      const refreshed = await fetch(`${API_BASE}/auth/refresh`, { method: "POST", credentials: "include" });
      if (refreshed.ok) response = await fetch(`${API_BASE}/auth/me`, { credentials: "include", cache: "no-store" });
    }
    if (response.ok) {
      const current = await response.json() as AuthUser;
      setUser(current);
      const previewingOnboarding = path === "/onboarding" && new URLSearchParams(window.location.search).get("preview") === "1";
      if ((path === "/onboarding" && !previewingOnboarding) || (path === "/auth" && current.account_type !== "guest")) router.replace("/");
      return;
    }
    setUser(null);
    if (!isPublic) {
      const onboarding = await fetch(`${API_BASE}/onboarding`, { credentials: "include", cache: "no-store" });
      const state = onboarding.ok ? await onboarding.json() : { completed: false };
      router.replace(state.completed ? "/auth" : "/onboarding");
    }
  }

  useEffect(() => {
    setChecking(true);
    loadUser().finally(() => setChecking(false));
  }, [path]);

  if (checking && !isPublic) {
    return (
      <main className="grid min-h-dvh place-items-center bg-background">
        <div className="grid place-items-center gap-3 text-muted-foreground">
          <div className="grid h-11 w-11 place-items-center rounded-xl border bg-card text-primary shadow-sm"><BookOpenCheck size={20} /></div>
          <span className="text-sm">Opening your workspace...</span>
        </div>
      </main>
    );
  }

  return <AuthContext.Provider value={{ user, refresh: loadUser }}>{children}</AuthContext.Provider>;
}
