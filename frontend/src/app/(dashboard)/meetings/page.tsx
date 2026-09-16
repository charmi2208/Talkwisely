"use client";

import { AppShell } from "@/components/layout/AppShell";
import { Construction } from "lucide-react";

export default function Page() {
  return (
    <AppShell title="Meetings" subtitle="Recorded video and audio meeting sessions">
      <div className="glass-card flex flex-col items-center justify-center p-16 text-center">
        <Construction className="w-12 h-12 text-indigo-600 mb-4" />
        <h2 className="text-xl font-bold text-slate-900 mb-1">Meetings Workspace</h2>
        <p className="text-slate-500 text-sm max-w-sm">Video and audio meeting integration with auto-transcription and meeting minutes generator.</p>
      </div>
    </AppShell>
  );
}
