"use client";

import { AppShell } from "@/components/layout/AppShell";
import { UserCircle } from "lucide-react";
import { useAuthStore } from "@/lib/stores/authStore";

export default function Page() {
  const { user } = useAuthStore();

  return (
    <AppShell title="Profile" subtitle="Manage your account profile and credentials">
      <div className="glass-card p-6 max-w-2xl space-y-6">
        <div className="flex items-center gap-4 border-b border-slate-200 pb-6">
          <div className="w-16 h-16 rounded-full bg-indigo-100 border border-indigo-200 flex items-center justify-center text-2xl font-bold text-indigo-700">
            {user?.full_name?.charAt(0) || "U"}
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900">{user?.full_name || "User Account"}</h2>
            <p className="text-sm text-slate-500">{user?.email}</p>
            <span className="inline-block mt-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-100 capitalize">
              Role: {user?.role || "agent"}
            </span>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Full Name</label>
            <input
              type="text"
              readOnly
              value={user?.full_name || ""}
              className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3.5 py-2 text-sm text-slate-800"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Email Address</label>
            <input
              type="email"
              readOnly
              value={user?.email || ""}
              className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3.5 py-2 text-sm text-slate-800"
            />
          </div>
        </div>
      </div>
    </AppShell>
  );
}
