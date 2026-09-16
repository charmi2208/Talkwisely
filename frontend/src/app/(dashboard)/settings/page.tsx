"use client";

import { AppShell } from "@/components/layout/AppShell";
import { Settings, Sliders, Bell, ShieldCheck } from "lucide-react";

export default function Page() {
  return (
    <AppShell title="Settings" subtitle="System preferences, notification thresholds & AI model configurations">
      <div className="glass-card p-6 max-w-3xl space-y-6">
        <h3 className="text-base font-bold text-slate-900 border-b border-slate-200 pb-3 flex items-center gap-2">
          <Settings className="w-5 h-5 text-indigo-600" />
          Application Preferences
        </h3>

        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-lg bg-slate-50 border border-slate-200">
            <div>
              <p className="text-sm font-semibold text-slate-900">Automatic Action Item Extraction</p>
              <p className="text-xs text-slate-500">Automatically extract tasks from uploaded call recordings using LLM pipeline</p>
            </div>
            <input type="checkbox" defaultChecked className="w-4 h-4 accent-indigo-600 rounded" />
          </div>

          <div className="flex items-center justify-between p-4 rounded-lg bg-slate-50 border border-slate-200">
            <div>
              <p className="text-sm font-semibold text-slate-900">Real-Time Lead Intent Alerts</p>
              <p className="text-xs text-slate-500">Receive notifications when a high-intent lead score (80+) is detected</p>
            </div>
            <input type="checkbox" defaultChecked className="w-4 h-4 accent-indigo-600 rounded" />
          </div>

          <div className="flex items-center justify-between p-4 rounded-lg bg-slate-50 border border-slate-200">
            <div>
              <p className="text-sm font-semibold text-slate-900">TalkWisely Cloud PBX Auto-Sync</p>
              <p className="text-xs text-slate-500">Sync new incoming calls from PBX webhook endpoints every 15 minutes</p>
            </div>
            <input type="checkbox" defaultChecked className="w-4 h-4 accent-indigo-600 rounded" />
          </div>
        </div>
      </div>
    </AppShell>
  );
}
