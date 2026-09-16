"use client";

import { AppShell } from "@/components/layout/AppShell";
import { Users } from "lucide-react";

export default function Page() {
  return (
    <AppShell title="Leads" subtitle="High-intent sales prospects and lead scoring dashboard">
      <div className="glass-card flex flex-col items-center justify-center p-16 text-center">
        <Users className="w-12 h-12 text-indigo-600 mb-4" />
        <h2 className="text-xl font-bold text-slate-900 mb-1">Leads Directory</h2>
        <p className="text-slate-500 text-sm max-w-sm">Manage conversation-qualified prospects and automated CRM lead syncing.</p>
      </div>
    </AppShell>
  );
}
