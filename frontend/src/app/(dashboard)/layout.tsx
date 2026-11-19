"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api/auth";
import { useAuthHydrated, useAuthStore } from "@/lib/stores/authStore";
import { Spinner } from "@/components/ui/spinner";

/**
 * Dashboard layout — wraps all protected pages.
 * Waits for the saved session to load, then redirects signed-out users to /login
 * and refreshes the signed-in user's profile (name and role may have changed).
 */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const hydrated = useAuthHydrated();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const setUser = useAuthStore((s) => s.setUser);

  useEffect(() => {
    if (!hydrated) return;
    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }
    authApi.me().then(setUser).catch(() => {
      // 401s are handled by the API client (refresh, or sign out)
    });
  }, [hydrated, isAuthenticated, router, setUser]);

  if (!hydrated || !isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Spinner className="size-6" />
      </div>
    );
  }

  return <>{children}</>;
}
