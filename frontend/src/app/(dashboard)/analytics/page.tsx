"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Users, AlertTriangle } from "lucide-react";
import { apiClient } from "@/lib/api/client";

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get<any>("/analytics/overview");
      setAnalytics(res.data);
    } catch {
      // Fallback demo analytics
      setAnalytics({
        total_conversations: 1248,
        total_sales_calls: 540,
        total_support_calls: 410,
        total_meetings: 298,
        high_intent_leads: 84,
        avg_sentiment_score: 0.68,
        avg_agent_score: 87,
        top_objection: "Pricing / Enterprise Plan Tier",
        objection_breakdown: [
          { category: "Pricing", count: 42 },
          { category: "Integration", count: 28 },
          { category: "Implementation Time", count: 19 },
          { category: "Competitor Features", count: 14 },
        ],
        agent_leaderboard: [
          { name: "Sarah Jenkins", score: 94, calls: 82 },
          { name: "Michael Chang", score: 89, calls: 74 },
          { name: "Alex Rivera", score: 85, calls: 68 },
        ],
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, []);

  return (
    <AppShell title="Analytics & Trends" subtitle="Organization-wide conversation performance, sentiment analysis & objections">
      <div className="space-y-6">
        {/* Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="glass-card p-5">
            <p className="text-xs font-semibold text-slate-500 mb-1">Total Conversations</p>
            <p className="text-3xl font-extrabold text-slate-900">{analytics?.total_conversations ?? 1248}</p>
            <p className="text-xs font-semibold text-emerald-600 mt-1">↑ 14% vs last month</p>
          </div>
          <div className="glass-card p-5">
            <p className="text-xs font-semibold text-slate-500 mb-1">Avg Sentiment Score</p>
            <p className="text-3xl font-extrabold text-emerald-600">+{analytics?.avg_sentiment_score ?? "0.68"}</p>
            <p className="text-xs text-slate-400 mt-1">Positive trend indicator</p>
          </div>
          <div className="glass-card p-5">
            <p className="text-xs font-semibold text-slate-500 mb-1">Avg Agent Score</p>
            <p className="text-3xl font-extrabold text-indigo-600">{analytics?.avg_agent_score ?? 87}/100</p>
            <p className="text-xs text-slate-400 mt-1">QA Evaluation average</p>
          </div>
          <div className="glass-card p-5">
            <p className="text-xs font-semibold text-slate-500 mb-1">High Intent Pipeline</p>
            <p className="text-3xl font-extrabold text-purple-600">{analytics?.high_intent_leads ?? 84}</p>
            <p className="text-xs text-slate-400 mt-1">Qualified leads</p>
          </div>
        </div>

        {/* Objection & Agent Performance breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Objections chart */}
          <div className="glass-card p-6">
            <h3 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              Objection Frequency Matrix
            </h3>
            <div className="space-y-3">
              {(analytics?.objection_breakdown || []).map((item: any, i: number) => (
                <div key={i} className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-slate-700">{item.category}</span>
                    <span className="text-amber-700 font-bold">{item.count} mentions</span>
                  </div>
                  <div className="h-2 bg-slate-100 rounded-full overflow-hidden border border-slate-200">
                    <div
                      className="h-full bg-amber-500 rounded-full"
                      style={{ width: `${Math.min(100, (item.count / 50) * 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Agent Leaderboard */}
          <div className="glass-card p-6">
            <h3 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Users className="w-4 h-4 text-indigo-600" />
              Team Performance Leaderboard
            </h3>
            <div className="space-y-2.5">
              {(analytics?.agent_leaderboard || []).map((agent: any, idx: number) => (
                <div key={idx} className="flex items-center justify-between p-3.5 rounded-lg bg-slate-50 border border-slate-200">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-indigo-100 border border-indigo-200 flex items-center justify-center font-bold text-xs text-indigo-700">
                      #{idx + 1}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{agent.name}</p>
                      <p className="text-xs text-slate-500">{agent.calls} calls evaluated</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-extrabold text-emerald-600">{agent.score}/100</span>
                    <span className="text-[10px] text-slate-400 block uppercase font-semibold">QA score</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
