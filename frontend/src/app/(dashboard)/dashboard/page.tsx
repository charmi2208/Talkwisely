"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import {
  TrendingUp, PhoneCall, CheckSquare, BarChart2,
  Upload, ArrowUpRight, Users, Clock, AlertTriangle,
} from "lucide-react";
import {
  AreaChart, Area, PieChart, Pie, Cell, Bar, BarChart,
  XAxis, YAxis, CartesianGrid,
} from "recharts";
import apiClient from "@/lib/api/client";
import type { Conversation } from "@/lib/api/conversations";
import {
  analyticsApi, type AnalyticsFilters, type AnalyticsOverview, type ObjectionStat,
  type SalesMetrics, type VolumePoint,
} from "@/lib/api/analytics";
import { apiErrorMessage } from "@/lib/api/errors";
import { formatDuration, humanize, shortDay } from "@/lib/format";
import { clsx } from "clsx";
import { AnalyticsFilterBar } from "@/components/analytics/AnalyticsFilterBar";
import { TrendBadge } from "@/components/analytics/TrendBadge";
import { ErrorState, PageLoading } from "@/components/common/ErrorState";
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

const SENTIMENT_COLORS: Record<string, string> = {
  positive: "#16a34a",
  negative: "#dc2626",
  neutral: "#64748b",
  mixed: "#d97706",
};

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

const intentChartConfig = {
  count: { label: "Conversations", theme: { light: "var(--chart-2)", dark: "var(--chart-1)" } },
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
  trend?: React.ReactNode;
}) {
  return (
    <Card className="@container/card">
      <CardHeader>
        <CardDescription className="flex items-center gap-2">
          <Icon className="size-4" />
          {title}
        </CardDescription>
        <CardTitle className="text-2xl font-semibold tabular-nums">{value}</CardTitle>
        {trend && <CardAction>{trend}</CardAction>}
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

interface DashboardData {
  overview: AnalyticsOverview;
  volume: VolumePoint[];
  sales: SalesMetrics;
  objections: ObjectionStat[];
  topics: { topic: string; count: number }[];
  recent: Conversation[];
}

export default function DashboardPage() {
  const [filters, setFilters] = useState<AnalyticsFilters>({ days: 30 });
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadData = useCallback(async () => {
    try {
      const [overview, volume, sales, objections, topics, convsRes] = await Promise.all([
        analyticsApi.overview(filters),
        analyticsApi.volume(filters),
        analyticsApi.sales(filters),
        analyticsApi.objections(filters),
        analyticsApi.topics({ ...filters }),
        apiClient.get("/conversations", {
          params: { page: 1, page_size: 5, conversation_type: filters.conversation_type },
        }),
      ]);
      setData({ overview, volume, sales, objections, topics, recent: convsRes.data.items || [] });
      setError("");
    } catch (err) {
      setError(apiErrorMessage(err, "The dashboard couldn't reach the API. Check that the backend is running."));
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const metrics = data?.overview;
  const periodLabel = `Last ${filters.days ?? 30} days`;

  const sentimentPieData = metrics
    ? Object.entries(metrics.sentiment_distribution).map(([k, v]) => ({
        key: k,
        name: k.charAt(0).toUpperCase() + k.slice(1),
        value: v,
        color: SENTIMENT_COLORS[k] || "#64748b",
      }))
    : [];

  const intentData = ["high", "medium", "low"].map((level) => ({
    level: humanize(level),
    count: data?.sales.purchase_intent_distribution[level] ?? 0,
  }));
  const maxObjection = Math.max(1, ...(data?.objections ?? []).map((o) => o.count));
  const hasVolume = (data?.volume ?? []).some((d) => d.total > 0);

  const quickActions = [
    { href: "/conversations", icon: Upload, title: "Upload Recording", description: "MP3, WAV, MP4" },
    { href: "/ai-assistant", icon: BarChart2, title: "AI Copilot", description: "Ask anything" },
    { href: "/action-items", icon: CheckSquare, title: "Action Items", description: `${metrics?.open_action_items ?? 0} open` },
    { href: "/analytics", icon: TrendingUp, title: "Analytics", description: "View trends" },
  ];

  return (
    <AppShell title="Dashboard" subtitle="Your AI conversation intelligence overview">
      <div className="space-y-6">
        <AnalyticsFilterBar value={filters} onChange={setFilters} />

        {loading && !data ? (
          <PageLoading />
        ) : error ? (
          <ErrorState message={error} onRetry={() => { setLoading(true); setError(""); loadData(); }} />
        ) : metrics && data ? (
          <>
            {/* KPI Metrics */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard
                title="Total Conversations"
                value={metrics.total_conversations}
                subtitle={`${metrics.total_calls} calls, ${metrics.total_meetings} meetings`}
                icon={PhoneCall}
                trend={<TrendBadge value={metrics.changes.total_conversations_pct} />}
              />
              <MetricCard
                title="High Intent Leads"
                value={metrics.high_intent_leads}
                subtitle={`${metrics.sales_opportunities} open sales opportunities`}
                icon={TrendingUp}
                trend={<TrendBadge value={metrics.changes.high_intent_leads_pct} />}
              />
              <MetricCard
                title="Open Action Items"
                value={metrics.open_action_items}
                subtitle={metrics.overdue_action_items ? `${metrics.overdue_action_items} overdue follow-ups` : "No overdue follow-ups"}
                icon={CheckSquare}
              />
              <MetricCard
                title="Avg Agent Score"
                value={metrics.average_agent_score ? `${metrics.average_agent_score}/100` : "N/A"}
                subtitle="AI-generated quality assessment"
                icon={BarChart2}
                trend={<TrendBadge value={metrics.changes.average_agent_score_points} unit=" pts" digits={1} />}
              />
            </div>

            {/* Secondary metrics */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <Card size="sm">
                <CardHeader>
                  <CardDescription>Avg Lead Score</CardDescription>
                  <CardTitle className="text-2xl font-semibold tabular-nums">
                    {metrics.average_lead_score}
                    <span className="text-xs font-normal text-muted-foreground">/100</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Progress value={metrics.average_lead_score} />
                </CardContent>
              </Card>
              <Card size="sm">
                <CardHeader>
                  <CardDescription>Average Sentiment</CardDescription>
                  <CardTitle className={clsx("capitalize",
                    metrics.dominant_sentiment === "positive" ? "text-success" :
                    metrics.dominant_sentiment === "negative" ? "text-destructive" : ""
                  )}>
                    {metrics.dominant_sentiment ?? "N/A"}
                  </CardTitle>
                </CardHeader>
                <CardFooter className="text-xs text-muted-foreground tabular-nums">
                  {metrics.average_sentiment_score !== null
                    ? `Score ${metrics.average_sentiment_score > 0 ? "+" : ""}${metrics.average_sentiment_score} (-1 to +1)`
                    : "No sentiment data yet"}
                </CardFooter>
              </Card>
              <Card size="sm">
                <CardHeader>
                  <CardDescription>Top Objection</CardDescription>
                  <CardTitle className="capitalize">
                    {metrics.top_objection_category ? humanize(metrics.top_objection_category) : "None"}
                  </CardTitle>
                </CardHeader>
                <CardFooter className="text-xs text-muted-foreground">
                  Avg call length {formatDuration(metrics.average_duration_seconds)}
                </CardFooter>
              </Card>
              <Card size="sm">
                <CardHeader>
                  <CardDescription>Processing Status</CardDescription>
                  <CardTitle className="tabular-nums">{metrics.completed_conversations} analyzed</CardTitle>
                </CardHeader>
                <CardFooter className="gap-3 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1"><Clock className="size-3.5" />{metrics.in_progress_conversations} in progress</span>
                  <span className="flex items-center gap-1"><AlertTriangle className="size-3.5" />{metrics.failed_conversations} failed</span>
                </CardFooter>
              </Card>
            </div>

            {/* Charts row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle>Conversation Volume</CardTitle>
                  <CardDescription>Calls and meetings per day, {periodLabel.toLowerCase()}</CardDescription>
                </CardHeader>
                <CardContent>
                  {hasVolume ? (
                    <ChartContainer config={trendChartConfig} className="aspect-auto h-[210px] w-full">
                      <AreaChart data={data.volume}>
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
                        <XAxis dataKey="date" tickLine={false} axisLine={false} tickMargin={8} tickFormatter={shortDay} minTickGap={24} />
                        <YAxis tickLine={false} axisLine={false} width={32} allowDecimals={false} />
                        <ChartTooltip cursor={false} content={<ChartTooltipContent indicator="dot" labelFormatter={(v) => shortDay(String(v))} />} />
                        <Area type="monotone" dataKey="calls" stroke="var(--color-calls)" strokeWidth={2} fill="url(#fillCalls)" />
                        <Area type="monotone" dataKey="meetings" stroke="var(--color-meetings)" strokeWidth={2} fill="url(#fillMeetings)" />
                      </AreaChart>
                    </ChartContainer>
                  ) : (
                    <div className="h-[210px] flex items-center justify-center text-muted-foreground text-sm">
                      No conversations in this period
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Sentiment Breakdown</CardTitle>
                  <CardDescription>{periodLabel}</CardDescription>
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

            {/* Sales intent, objections, topics */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Sales Intent</CardTitle>
                  <CardDescription>Purchase intent detected in sales conversations</CardDescription>
                </CardHeader>
                <CardContent>
                  {intentData.some((d) => d.count > 0) ? (
                    <ChartContainer config={intentChartConfig} className="aspect-auto h-[160px] w-full">
                      <BarChart data={intentData}>
                        <CartesianGrid vertical={false} />
                        <XAxis dataKey="level" tickLine={false} axisLine={false} />
                        <YAxis tickLine={false} axisLine={false} width={28} allowDecimals={false} />
                        <ChartTooltip cursor={false} content={<ChartTooltipContent hideLabel />} />
                        <Bar dataKey="count" fill="var(--color-count)" radius={4} />
                      </BarChart>
                    </ChartContainer>
                  ) : (
                    <div className="h-[160px] flex items-center justify-center text-muted-foreground text-sm">No sales calls scored yet</div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Top Objections</CardTitle>
                  <CardDescription>Most frequent customer objections</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {data.objections.length === 0 && <p className="text-sm text-muted-foreground">No objections recorded</p>}
                  {data.objections.slice(0, 5).map((o) => (
                    <div key={o.category} className="space-y-1">
                      <div className="flex justify-between text-xs font-medium">
                        <span className="capitalize">{humanize(o.category)}</span>
                        <span className="text-muted-foreground tabular-nums">{o.count} ({Math.round(o.resolution_rate * 100)}% resolved)</span>
                      </div>
                      <Progress value={(o.count / maxObjection) * 100} className="h-2" />
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Topic Trends</CardTitle>
                  <CardDescription>Most discussed topics</CardDescription>
                </CardHeader>
                <CardContent>
                  {data.topics.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No topics yet</p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {data.topics.map((t) => (
                        <Badge key={t.topic} variant="secondary" className="gap-1.5">
                          {t.topic}
                          <span className="tabular-nums text-muted-foreground">{t.count}</span>
                        </Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Recent conversations + Quick actions */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
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
                  {data.recent.length === 0 ? (
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
                      {data.recent.map((conv) => (
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
                                <span className="capitalize">{humanize(conv.conversation_type)}</span>
                                <span className="capitalize">{conv.status}</span>
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
          </>
        ) : null}
      </div>
    </AppShell>
  );
}
