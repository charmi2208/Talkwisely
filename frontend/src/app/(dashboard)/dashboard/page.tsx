"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import {
  TrendingUp, PhoneCall, CheckSquare, BarChart2,
  Upload, ArrowUpRight, Loader2,
} from "lucide-react";
import {
  AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import apiClient from "@/lib/api/client";
import { clsx } from "clsx";

interface DashboardMetrics {
  total_conversations: number;
  completed_conversations: number;
  high_intent_leads: number;
  open_action_items: number;
  average_lead_score: number;
  average_agent_score: number;
  dominant_sentiment: string;
  top_objection_category: string;
  sentiment_distribution: Record<string, number>;
  conversations_by_type: Record<string, number>;
}

const SENTIMENT_COLORS: Record<string, string> = {
  positive: "#16a34a",
  negative: "#dc2626",
  neutral: "#64748b",
  mixed: "#d97706",
};

// Mock trend data for charts
const CONV_TREND_DATA = [
  { date: "Mon", calls: 12, meetings: 4 },
  { date: "Tue", calls: 18, meetings: 6 },
  { date: "Wed", calls: 15, meetings: 3 },
  { date: "Thu", calls: 22, meetings: 8 },
  { date: "Fri", calls: 19, meetings: 5 },
  { date: "Sat", calls: 8, meetings: 2 },
  { date: "Sun", calls: 5, meetings: 1 },
];

function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  color = "blue",
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ElementType;
  trend?: number;
  color?: "blue" | "green" | "purple" | "orange" | "red";
}) {
  const colorMap = {
    blue: "bg-indigo-50 text-indigo-600 border-indigo-100",
    green: "bg-emerald-50 text-emerald-600 border-emerald-100",
    purple: "bg-purple-50 text-purple-600 border-purple-100",
    orange: "bg-amber-50 text-amber-600 border-amber-100",
    red: "bg-rose-50 text-rose-600 border-rose-100",
  };

  return (
    <div className="metric-card bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
      <div className="flex items-start justify-between mb-3">
        <div className={clsx("p-2 rounded-lg border", colorMap[color])}>
          <Icon className="w-5 h-5" />
        </div>
        {trend !== undefined && (
          <div className={clsx("flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full border",
            trend >= 0 ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-rose-50 text-rose-700 border-rose-200"
          )}>
            <ArrowUpRight className={clsx("w-3 h-3", trend < 0 && "rotate-90")} />
            {Math.abs(trend)}%
          </div>
        )}
      </div>
      <div className="text-2xl font-bold text-slate-900 tracking-tight mb-0.5">{value}</div>
      <div className="text-xs font-semibold text-slate-600">{title}</div>
      {subtitle && <div className="text-xs text-slate-400 mt-0.5">{subtitle}</div>}
    </div>
  );
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [recentConversations, setRecentConversations] = useState<any[]>([]);

  useEffect(() => {
    async function loadData() {
      try {
        const [metricsRes, convsRes] = await Promise.all([
          apiClient.get("/analytics/overview?days=30"),
          apiClient.get("/conversations?page=1&page_size=5"),
        ]);
        setMetrics(metricsRes.data);
        setRecentConversations(convsRes.data.items || []);
      } catch (err) {
        console.error("Failed to load dashboard data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const sentimentPieData = metrics
    ? Object.entries(metrics.sentiment_distribution).map(([k, v]) => ({
        name: k.charAt(0).toUpperCase() + k.slice(1),
        value: v,
        color: SENTIMENT_COLORS[k] || "#64748b",
      }))
    : [];

  return (
    <AppShell title="Dashboard" subtitle="Your AI conversation intelligence overview">
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* KPI Metrics */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title="Total Conversations"
              value={metrics?.total_conversations ?? 0}
              subtitle="Last 30 days"
              icon={PhoneCall}
              trend={12}
              color="blue"
            />
            <MetricCard
              title="High Intent Leads"
              value={metrics?.high_intent_leads ?? 0}
              subtitle="Purchase intent: high"
              icon={TrendingUp}
              trend={8}
              color="green"
            />
            <MetricCard
              title="Open Action Items"
              value={metrics?.open_action_items ?? 0}
              subtitle="Pending tasks"
              icon={CheckSquare}
              color="orange"
            />
            <MetricCard
              title="Avg Agent Score"
              value={metrics?.average_agent_score ? `${metrics.average_agent_score}/100` : "N/A"}
              subtitle="AI quality assessment"
              icon={BarChart2}
              trend={3}
              color="purple"
            />
          </div>

          {/* Secondary metrics */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="glass-card p-4 col-span-1">
              <div className="text-xs font-medium text-slate-500 mb-1">Avg Lead Score</div>
              <div className="text-2xl font-bold text-slate-900">{metrics?.average_lead_score ?? 0}<span className="text-xs font-normal text-slate-400">/100</span></div>
              <div className="mt-2 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full bg-indigo-600 rounded-full" style={{ width: `${metrics?.average_lead_score ?? 0}%` }} />
              </div>
            </div>
            <div className="glass-card p-4 col-span-1">
              <div className="text-xs font-medium text-slate-500 mb-1">Dominant Sentiment</div>
              <div className={clsx("text-base font-semibold capitalize mt-1",
                metrics?.dominant_sentiment === "positive" ? "text-emerald-700" :
                metrics?.dominant_sentiment === "negative" ? "text-rose-700" : "text-slate-700"
              )}>
                {metrics?.dominant_sentiment ?? "N/A"}
              </div>
            </div>
            <div className="glass-card p-4 col-span-1">
              <div className="text-xs font-medium text-slate-500 mb-1">Top Objection</div>
              <div className="text-base font-semibold text-amber-700 capitalize mt-1">
                {metrics?.top_objection_category ?? "None"}
              </div>
            </div>
            <div className="glass-card p-4 col-span-1">
              <div className="text-xs font-medium text-slate-500 mb-1">Completed Analysis</div>
              <div className="text-base font-semibold text-slate-900 mt-1">
                {metrics?.completed_conversations ?? 0}
              </div>
            </div>
          </div>

          {/* Charts row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Conversation trend */}
            <div className="lg:col-span-2 glass-card p-5">
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Conversation Volume</h3>
                  <p className="text-xs text-slate-500">Calls and meetings this week</p>
                </div>
              </div>
              <ResponsiveContainer width="100%" height={210}>
                <AreaChart data={CONV_TREND_DATA}>
                  <defs>
                    <linearGradient id="callsGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#4f46e5" stopOpacity={0.15} />
                      <stop offset="100%" stopColor="#4f46e5" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="meetingsGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#9333ea" stopOpacity={0.15} />
                      <stop offset="100%" stopColor="#9333ea" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: "#64748b", fontSize: 12 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "8px", color: "#0f172a", boxShadow: "0 4px 12px rgba(15, 23, 42, 0.08)" }}
                  />
                  <Area type="monotone" dataKey="calls" stroke="#4f46e5" strokeWidth={2} fill="url(#callsGrad)" name="Calls" />
                  <Area type="monotone" dataKey="meetings" stroke="#9333ea" strokeWidth={2} fill="url(#meetingsGrad)" name="Meetings" />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Sentiment pie */}
            <div className="glass-card p-5">
              <div className="mb-4">
                <h3 className="text-sm font-bold text-slate-900">Sentiment Breakdown</h3>
                <p className="text-xs text-slate-500">Last 30 days</p>
              </div>
              {sentimentPieData.length > 0 ? (
                <ResponsiveContainer width="100%" height={140}>
                  <PieChart>
                    <Pie data={sentimentPieData} cx="50%" cy="50%" outerRadius={55} dataKey="value">
                      {sentimentPieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "8px", boxShadow: "0 4px 12px rgba(15, 23, 42, 0.08)" }} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-32 flex items-center justify-center text-slate-400 text-sm">
                  No data yet
                </div>
              )}
              <div className="space-y-1.5 mt-2">
                {sentimentPieData.map((s) => (
                  <div key={s.name} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-full" style={{ background: s.color }} />
                      <span className="text-slate-600 font-medium">{s.name}</span>
                    </div>
                    <span className="text-slate-900 font-semibold">{s.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Recent conversations + Quick actions */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Recent conversations */}
            <div className="lg:col-span-2 glass-card p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold text-slate-900">Recent Conversations</h3>
                <Link href="/conversations" className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 flex items-center gap-1">
                  View all <ArrowUpRight className="w-3.5 h-3.5" />
                </Link>
              </div>
              <div className="space-y-2.5">
                {recentConversations.length === 0 ? (
                  <div className="text-center py-8 text-slate-400">
                    <PhoneCall className="w-8 h-8 mx-auto mb-2 opacity-40 text-slate-400" />
                    <p className="text-sm font-medium text-slate-600">No conversations yet</p>
                    <p className="text-xs text-slate-400 mt-0.5">Upload your first recording to get started</p>
                  </div>
                ) : (
                  recentConversations.map((conv) => (
                    <Link
                      key={conv.id}
                      href={`/conversations/${conv.id}`}
                      className="flex items-center gap-4 p-3 rounded-lg bg-slate-50 border border-slate-100 hover:bg-slate-100/80 hover:border-slate-200 transition-all group"
                    >
                      <div className={clsx("w-2 h-2 rounded-full flex-shrink-0",
                        conv.status === "completed" ? "bg-emerald-500" :
                        conv.status === "failed" ? "bg-rose-500" : "bg-amber-500 animate-pulse"
                      )} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-900 truncate group-hover:text-indigo-600 transition-colors">{conv.title}</p>
                        <div className="flex items-center gap-3 mt-0.5">
                          <span className="text-xs text-slate-500 capitalize">{conv.conversation_type.replace("_", " ")}</span>
                          {conv.duration_seconds && (
                            <span className="text-xs text-slate-400">{Math.round(conv.duration_seconds / 60)}m</span>
                          )}
                          {conv.lead_score && (
                            <span className="text-xs text-indigo-600 font-semibold">Score: {conv.lead_score}</span>
                          )}
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0">
                        {conv.overall_sentiment && (
                          <span className={clsx("text-xs px-2.5 py-1 rounded-full font-medium capitalize border",
                            conv.overall_sentiment === "positive" ? "badge-positive" :
                            conv.overall_sentiment === "negative" ? "badge-negative" : "badge-neutral"
                          )}>
                            {conv.overall_sentiment}
                          </span>
                        )}
                      </div>
                    </Link>
                  ))
                )}
              </div>
            </div>

            {/* Quick actions */}
            <div className="glass-card p-5">
              <h3 className="text-sm font-bold text-slate-900 mb-4">Quick Actions</h3>
              <div className="space-y-2.5">
                <Link
                  href="/conversations"
                  className="flex items-center gap-3 p-3 rounded-lg bg-indigo-50/60 border border-indigo-100 hover:bg-indigo-50 transition-all group"
                >
                  <Upload className="w-5 h-5 text-indigo-600" />
                  <div>
                    <p className="text-sm font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors">Upload Recording</p>
                    <p className="text-xs text-slate-500">MP3, WAV, MP4</p>
                  </div>
                </Link>
                <Link
                  href="/ai-assistant"
                  className="flex items-center gap-3 p-3 rounded-lg bg-purple-50/60 border border-purple-100 hover:bg-purple-50 transition-all group"
                >
                  <BarChart2 className="w-5 h-5 text-purple-600" />
                  <div>
                    <p className="text-sm font-semibold text-slate-900 group-hover:text-purple-600 transition-colors">AI Copilot</p>
                    <p className="text-xs text-slate-500">Ask anything</p>
                  </div>
                </Link>
                <Link
                  href="/action-items"
                  className="flex items-center gap-3 p-3 rounded-lg bg-amber-50/60 border border-amber-100 hover:bg-amber-50 transition-all group"
                >
                  <CheckSquare className="w-5 h-5 text-amber-600" />
                  <div>
                    <p className="text-sm font-semibold text-slate-900 group-hover:text-amber-600 transition-colors">Action Items</p>
                    <p className="text-xs text-slate-500">
                      {metrics?.open_action_items ?? 0} pending
                    </p>
                  </div>
                </Link>
                <Link
                  href="/analytics"
                  className="flex items-center gap-3 p-3 rounded-lg bg-emerald-50/60 border border-emerald-100 hover:bg-emerald-50 transition-all group"
                >
                  <TrendingUp className="w-5 h-5 text-emerald-600" />
                  <div>
                    <p className="text-sm font-semibold text-slate-900 group-hover:text-emerald-600 transition-colors">Analytics</p>
                    <p className="text-xs text-slate-500">View trends</p>
                  </div>
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
