"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import {
  TrendingUp, PhoneCall, CheckSquare, BarChart2,
  Upload, ArrowUpRight,
} from "lucide-react";
import {
  AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid,
} from "recharts";
import apiClient from "@/lib/api/client";
import { clsx } from "clsx";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle,
} from "@/components/ui/card";
import {
  ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig,
} from "@/components/ui/chart";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import {
  Item, ItemActions, ItemContent, ItemDescription, ItemGroup, ItemMedia, ItemTitle,
} from "@/components/ui/item";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";

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

// Dark mode shifts both series one step lighter so they stay visible on dark cards
const trendChartConfig = {
  calls: { label: "Calls", theme: { light: "var(--chart-2)", dark: "var(--chart-1)" } },
  meetings: { label: "Meetings", theme: { light: "var(--chart-4)", dark: "var(--chart-3)" } },
} satisfies ChartConfig;

const sentimentChartConfig = {
  value: { label: "Conversations" },
  positive: { label: "Positive", color: SENTIMENT_COLORS.positive },
  negative: { label: "Negative", color: SENTIMENT_COLORS.negative },
  neutral: { label: "Neutral", color: SENTIMENT_COLORS.neutral },
  mixed: { label: "Mixed", color: SENTIMENT_COLORS.mixed },
} satisfies ChartConfig;

function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ElementType;
  trend?: number;
}) {
  return (
    <Card className="@container/card">
      <CardHeader>
        <CardDescription className="flex items-center gap-2">
          <Icon className="size-4" />
          {title}
        </CardDescription>
        <CardTitle className="text-2xl font-semibold tabular-nums">{value}</CardTitle>
        {trend !== undefined && (
          <CardAction>
            <Badge variant="outline">
              <ArrowUpRight className={clsx(trend < 0 && "rotate-90")} />
              {Math.abs(trend)}%
            </Badge>
          </CardAction>
        )}
      </CardHeader>
      {subtitle && (
        <CardFooter className="text-sm text-muted-foreground">{subtitle}</CardFooter>
      )}
    </Card>
  );
}

function SentimentBadge({ sentiment }: { sentiment: string }) {
  return (
    <Badge
      variant={sentiment === "negative" ? "destructive" : sentiment === "positive" ? "secondary" : "outline"}
      className="capitalize"
    >
      {sentiment}
    </Badge>
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
        key: k,
        name: k.charAt(0).toUpperCase() + k.slice(1),
        value: v,
        color: SENTIMENT_COLORS[k] || "#64748b",
      }))
    : [];

  const quickActions = [
    { href: "/conversations", icon: Upload, title: "Upload Recording", description: "MP3, WAV, MP4" },
    { href: "/ai-assistant", icon: BarChart2, title: "AI Copilot", description: "Ask anything" },
    { href: "/action-items", icon: CheckSquare, title: "Action Items", description: `${metrics?.open_action_items ?? 0} pending` },
    { href: "/analytics", icon: TrendingUp, title: "Analytics", description: "View trends" },
  ];

  return (
    <AppShell title="Dashboard" subtitle="Your AI conversation intelligence overview">
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Spinner className="size-8" />
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
            />
            <MetricCard
              title="High Intent Leads"
              value={metrics?.high_intent_leads ?? 0}
              subtitle="Purchase intent: high"
              icon={TrendingUp}
              trend={8}
            />
            <MetricCard
              title="Open Action Items"
              value={metrics?.open_action_items ?? 0}
              subtitle="Pending tasks"
              icon={CheckSquare}
            />
            <MetricCard
              title="Avg Agent Score"
              value={metrics?.average_agent_score ? `${metrics.average_agent_score}/100` : "N/A"}
              subtitle="AI quality assessment"
              icon={BarChart2}
              trend={3}
            />
          </div>

          {/* Secondary metrics */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Card size="sm">
              <CardHeader>
                <CardDescription>Avg Lead Score</CardDescription>
                <CardTitle className="text-2xl font-semibold tabular-nums">
                  {metrics?.average_lead_score ?? 0}
                  <span className="text-xs font-normal text-muted-foreground">/100</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Progress value={metrics?.average_lead_score ?? 0} />
              </CardContent>
            </Card>
            <Card size="sm">
              <CardHeader>
                <CardDescription>Dominant Sentiment</CardDescription>
                <CardTitle className={clsx("capitalize",
                  metrics?.dominant_sentiment === "positive" ? "text-success" :
                  metrics?.dominant_sentiment === "negative" ? "text-destructive" : ""
                )}>
                  {metrics?.dominant_sentiment ?? "N/A"}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card size="sm">
              <CardHeader>
                <CardDescription>Top Objection</CardDescription>
                <CardTitle className="capitalize">
                  {metrics?.top_objection_category ?? "None"}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card size="sm">
              <CardHeader>
                <CardDescription>Completed Analysis</CardDescription>
                <CardTitle>{metrics?.completed_conversations ?? 0}</CardTitle>
              </CardHeader>
            </Card>
          </div>

          {/* Charts row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Conversation trend */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Conversation Volume</CardTitle>
                <CardDescription>Calls and meetings this week</CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer config={trendChartConfig} className="aspect-auto h-[210px] w-full">
                  <AreaChart data={CONV_TREND_DATA}>
                    <defs>
                      <linearGradient id="fillCalls" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--color-calls)" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="var(--color-calls)" stopOpacity={0.05} />
                      </linearGradient>
                      <linearGradient id="fillMeetings" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--color-meetings)" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="var(--color-meetings)" stopOpacity={0.05} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid vertical={false} />
                    <XAxis dataKey="date" tickLine={false} axisLine={false} tickMargin={8} />
                    <YAxis tickLine={false} axisLine={false} width={32} />
                    <ChartTooltip cursor={false} content={<ChartTooltipContent indicator="dot" />} />
                    <Area type="monotone" dataKey="calls" stroke="var(--color-calls)" strokeWidth={2} fill="url(#fillCalls)" />
                    <Area type="monotone" dataKey="meetings" stroke="var(--color-meetings)" strokeWidth={2} fill="url(#fillMeetings)" />
                  </AreaChart>
                </ChartContainer>
              </CardContent>
            </Card>

            {/* Sentiment pie */}
            <Card>
              <CardHeader>
                <CardTitle>Sentiment Breakdown</CardTitle>
                <CardDescription>Last 30 days</CardDescription>
              </CardHeader>
              <CardContent>
                {sentimentPieData.length > 0 ? (
                  <ChartContainer config={sentimentChartConfig} className="aspect-auto h-[140px] w-full">
                    <PieChart>
                      <ChartTooltip content={<ChartTooltipContent nameKey="key" hideLabel />} />
                      <Pie data={sentimentPieData} cx="50%" cy="50%" outerRadius={55} dataKey="value" nameKey="key">
                        {sentimentPieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                    </PieChart>
                  </ChartContainer>
                ) : (
                  <div className="h-32 flex items-center justify-center text-muted-foreground text-sm">
                    No data yet
                  </div>
                )}
                <div className="space-y-1.5 mt-2">
                  {sentimentPieData.map((s) => (
                    <div key={s.name} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <div className="size-2.5 rounded-full" style={{ background: s.color }} />
                        <span className="text-muted-foreground font-medium">{s.name}</span>
                      </div>
                      <span className="font-semibold tabular-nums">{s.value}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Recent conversations + Quick actions */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Recent conversations */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Recent Conversations</CardTitle>
                <CardAction>
                  <Button variant="ghost" size="sm" asChild>
                    <Link href="/conversations">
                      View all <ArrowUpRight data-icon="inline-end" />
                    </Link>
                  </Button>
                </CardAction>
              </CardHeader>
              <CardContent>
                {recentConversations.length === 0 ? (
                  <Empty>
                    <EmptyHeader>
                      <EmptyMedia variant="icon">
                        <PhoneCall />
                      </EmptyMedia>
                      <EmptyTitle>No conversations yet</EmptyTitle>
                      <EmptyDescription>Upload your first recording to get started</EmptyDescription>
                    </EmptyHeader>
                  </Empty>
                ) : (
                  <ItemGroup className="gap-2">
                    {recentConversations.map((conv) => (
                      <Item key={conv.id} variant="outline" size="sm" asChild>
                        <Link href={`/conversations/${conv.id}`}>
                          <ItemMedia>
                            <span className={clsx("size-2 rounded-full",
                              conv.status === "completed" ? "bg-emerald-500" :
                              conv.status === "failed" ? "bg-destructive" : "bg-amber-500 animate-pulse"
                            )} />
                          </ItemMedia>
                          <ItemContent className="min-w-0">
                            <ItemTitle>{conv.title}</ItemTitle>
                            <ItemDescription className="flex items-center gap-3 text-xs">
                              <span className="capitalize">{conv.conversation_type.replace("_", " ")}</span>
                              {conv.duration_seconds && (
                                <span>{Math.round(conv.duration_seconds / 60)}m</span>
                              )}
                              {conv.lead_score && (
                                <span className="font-semibold text-foreground">Score: {conv.lead_score}</span>
                              )}
                            </ItemDescription>
                          </ItemContent>
                          {conv.overall_sentiment && (
                            <ItemActions>
                              <SentimentBadge sentiment={conv.overall_sentiment} />
                            </ItemActions>
                          )}
                        </Link>
                      </Item>
                    ))}
                  </ItemGroup>
                )}
              </CardContent>
            </Card>

            {/* Quick actions */}
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
              </CardHeader>
              <CardContent>
                <ItemGroup className="gap-2">
                  {quickActions.map((action) => (
                    <Item key={action.href} variant="outline" size="sm" asChild>
                      <Link href={action.href}>
                        <ItemMedia variant="icon">
                          <action.icon className="size-5" />
                        </ItemMedia>
                        <ItemContent>
                          <ItemTitle>{action.title}</ItemTitle>
                          <ItemDescription className="text-xs">{action.description}</ItemDescription>
                        </ItemContent>
                      </Link>
                    </Item>
                  ))}
                </ItemGroup>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </AppShell>
  );
}
