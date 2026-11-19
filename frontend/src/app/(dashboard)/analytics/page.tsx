"use client";

import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Users, AlertTriangle, TrendingUp, Swords } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";
import {
  analyticsApi, type AgentPerformance, type AnalyticsFilters, type AnalyticsOverview,
  type ObjectionStat, type SalesMetrics, type SentimentPoint, type VolumePoint,
} from "@/lib/api/analytics";
import { apiErrorMessage } from "@/lib/api/errors";
import { formatDuration, humanize, shortDay } from "@/lib/format";
import { PIPELINE_STAGES } from "@/lib/api/sales";
import { AnalyticsFilterBar } from "@/components/analytics/AnalyticsFilterBar";
import { TrendBadge } from "@/components/analytics/TrendBadge";
import { ErrorState, PageLoading } from "@/components/common/ErrorState";
import { Badge } from "@/components/ui/badge";
import {
  Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle,
} from "@/components/ui/card";
import {
  ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent, type ChartConfig,
} from "@/components/ui/chart";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const sentimentConfig = {
  positive: { label: "Positive", color: "#16a34a" },
  neutral: { label: "Neutral", color: "#64748b" },
  mixed: { label: "Mixed", color: "#d97706" },
  negative: { label: "Negative", color: "#dc2626" },
} satisfies ChartConfig;

const stageConfig = {
  count: { label: "Leads", theme: { light: "var(--chart-2)", dark: "var(--chart-1)" } },
} satisfies ChartConfig;

const durationConfig = {
  minutes: { label: "Avg minutes", theme: { light: "var(--chart-3)", dark: "var(--chart-2)" } },
} satisfies ChartConfig;

interface AnalyticsData {
  overview: AnalyticsOverview;
  sentiment: SentimentPoint[];
  objections: ObjectionStat[];
  sales: SalesMetrics;
  agents: AgentPerformance;
  volume: VolumePoint[];
}

function score(value: number | null | undefined) {
  return value === null || value === undefined ? "-" : Math.round(value);
}

export default function AnalyticsPage() {
  const [filters, setFilters] = useState<AnalyticsFilters>({ days: 30 });
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [overview, sentiment, objections, sales, agents, volume] = await Promise.all([
        analyticsApi.overview(filters),
        analyticsApi.sentiment(filters),
        analyticsApi.objections(filters),
        analyticsApi.sales(filters),
        analyticsApi.agents(filters),
        analyticsApi.volume(filters),
      ]);
      setData({ overview, sentiment, objections, sales, agents, volume });
      setError("");
    } catch (err) {
      setError(apiErrorMessage(err, "Analytics couldn't be loaded. Check that the backend is running."));
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    load();
  }, [load]);

  const o = data?.overview;
  const maxObjection = Math.max(1, ...(data?.objections ?? []).map((x) => x.count));
  const stageData = PIPELINE_STAGES.map((stage) => ({
    stage: humanize(stage),
    count: data?.sales.pipeline_stage_distribution[stage] ?? 0,
  }));
  const durationData = (data?.volume ?? [])
    .filter((d) => d.avg_duration_seconds)
    .map((d) => ({ date: d.date, minutes: Math.round(((d.avg_duration_seconds ?? 0) / 60) * 10) / 10 }));

  return (
    <AppShell title="Analytics & Trends" subtitle="Organization-wide conversation performance, sentiment analysis & objections">
      <div className="space-y-6">
        <AnalyticsFilterBar value={filters} onChange={setFilters} />

        {loading && !data ? (
          <PageLoading />
        ) : error ? (
          <ErrorState message={error} onRetry={() => { setLoading(true); setError(""); load(); }} />
        ) : o && data ? (
          <>
            {/* Metric Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card>
                <CardHeader>
                  <CardDescription>Total Conversations</CardDescription>
                  <CardTitle className="text-3xl font-semibold tabular-nums">{o.total_conversations}</CardTitle>
                  <CardAction><TrendBadge value={o.changes.total_conversations_pct} /></CardAction>
                </CardHeader>
                <CardFooter className="text-xs text-muted-foreground">
                  {o.changes.total_conversations_pct === null ? "No earlier period to compare" : "vs previous period"}
                </CardFooter>
              </Card>
              <Card>
                <CardHeader>
                  <CardDescription>Avg Sentiment Score</CardDescription>
                  <CardTitle className="text-3xl font-semibold tabular-nums">
                    {o.average_sentiment_score === null ? "N/A" : `${o.average_sentiment_score > 0 ? "+" : ""}${o.average_sentiment_score}`}
                  </CardTitle>
                  <CardAction><TrendBadge value={o.changes.average_sentiment_score_points} unit="" digits={2} /></CardAction>
                </CardHeader>
                <CardFooter className="text-xs text-muted-foreground">Scale -1 (negative) to +1 (positive)</CardFooter>
              </Card>
              <Card>
                <CardHeader>
                  <CardDescription>Avg Agent Score</CardDescription>
                  <CardTitle className="text-3xl font-semibold tabular-nums">
                    {o.average_agent_score ? `${o.average_agent_score}/100` : "N/A"}
                  </CardTitle>
                  <CardAction><TrendBadge value={o.changes.average_agent_score_points} unit=" pts" digits={1} /></CardAction>
                </CardHeader>
                <CardFooter className="text-xs text-muted-foreground">AI-generated QA assessment</CardFooter>
              </Card>
              <Card>
                <CardHeader>
                  <CardDescription>High Intent Pipeline</CardDescription>
                  <CardTitle className="text-3xl font-semibold tabular-nums">{o.high_intent_leads}</CardTitle>
                  <CardAction><TrendBadge value={o.changes.high_intent_leads_pct} /></CardAction>
                </CardHeader>
                <CardFooter className="text-xs text-muted-foreground">
                  {o.average_closing_probability !== null
                    ? `Avg closing probability ${Math.round(o.average_closing_probability * 100)}%`
                    : "Purchase intent: high"}
                </CardFooter>
              </Card>
            </div>

            {/* Sentiment trend */}
            <Card>
              <CardHeader>
                <CardTitle>Sentiment Trend</CardTitle>
                <CardDescription>Conversations by overall customer sentiment per day</CardDescription>
              </CardHeader>
              <CardContent>
                {data.sentiment.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No sentiment data in this period</p>
                ) : (
                  <ChartContainer config={sentimentConfig} className="aspect-auto h-[240px] w-full">
                    <BarChart data={data.sentiment}>
                      <CartesianGrid vertical={false} />
                      <XAxis dataKey="date" tickLine={false} axisLine={false} tickFormatter={shortDay} minTickGap={24} />
                      <YAxis tickLine={false} axisLine={false} width={28} allowDecimals={false} />
                      <ChartTooltip content={<ChartTooltipContent labelFormatter={(v) => shortDay(String(v))} />} />
                      <ChartLegend content={<ChartLegendContent />} />
                      {(["positive", "neutral", "mixed", "negative"] as const).map((key) => (
                        <Bar key={key} dataKey={key} stackId="sentiment" fill={`var(--color-${key})`} />
                      ))}
                    </BarChart>
                  </ChartContainer>
                )}
              </CardContent>
            </Card>

            {/* Objection & Agent Performance breakdown */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <AlertTriangle className="size-4 text-warning" />
                    Objection Frequency Matrix
                  </CardTitle>
                  <CardDescription>How often each objection came up and how many were resolved on the call</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {data.objections.length === 0 && <p className="text-sm text-muted-foreground">No objections recorded</p>}
                  {data.objections.map((item) => (
                    <div key={item.category} className="space-y-1.5">
                      <div className="flex justify-between gap-2 text-xs font-medium">
                        <span className="capitalize">{humanize(item.category)}</span>
                        <span className="text-muted-foreground tabular-nums">
                          {item.count} mentions, {item.resolved} resolved, severity {item.avg_severity.toFixed(1)}/3
                        </span>
                      </div>
                      <Progress
                        value={(item.count / maxObjection) * 100}
                        className="h-2 *:data-[slot=progress-indicator]:bg-amber-500"
                      />
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Users className="size-4" />
                    Team Performance Leaderboard
                  </CardTitle>
                  <CardDescription>{data.agents.disclaimer}</CardDescription>
                </CardHeader>
                <CardContent>
                  {data.agents.leaderboard.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No scored conversations in this period</p>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>#</TableHead>
                          <TableHead>Person</TableHead>
                          <TableHead className="text-right">Calls</TableHead>
                          <TableHead className="text-right">Overall</TableHead>
                          <TableHead className="text-right">Empathy</TableHead>
                          <TableHead className="text-right">Objections</TableHead>
                          <TableHead className="text-right">Closing</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.agents.leaderboard.map((person, idx) => (
                          <TableRow key={person.user_id}>
                            <TableCell className="text-muted-foreground tabular-nums">{idx + 1}</TableCell>
                            <TableCell className="font-medium">{person.name}</TableCell>
                            <TableCell className="text-right tabular-nums">{person.conversations_scored}</TableCell>
                            <TableCell className="text-right font-semibold tabular-nums">{score(person.scores.overall)}</TableCell>
                            <TableCell className="text-right tabular-nums">{score(person.scores.empathy)}</TableCell>
                            <TableCell className="text-right tabular-nums">{score(person.scores.objection_handling)}</TableCell>
                            <TableCell className="text-right tabular-nums">{score(person.scores.closing)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Sales, competitors, duration */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="size-4" />
                    Pipeline Stages
                  </CardTitle>
                  <CardDescription>
                    Deal health:{" "}
                    {Object.entries(data.sales.deal_health_distribution).map(([k, v]) => `${humanize(k)} ${v}`).join(", ") || "no data"}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ChartContainer config={stageConfig} className="aspect-auto h-[200px] w-full">
                    <BarChart data={stageData}>
                      <CartesianGrid vertical={false} />
                      <XAxis dataKey="stage" tickLine={false} axisLine={false} interval={0} fontSize={11} />
                      <YAxis tickLine={false} axisLine={false} width={28} allowDecimals={false} />
                      <ChartTooltip cursor={false} content={<ChartTooltipContent hideLabel />} />
                      <Bar dataKey="count" fill="var(--color-count)" radius={4} />
                    </BarChart>
                  </ChartContainer>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Swords className="size-4" />
                    Competitor Mentions
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {data.sales.top_competitors.length === 0 && <p className="text-sm text-muted-foreground">No competitors mentioned</p>}
                  {data.sales.top_competitors.map((c) => (
                    <div key={c.name} className="flex items-center justify-between text-sm">
                      <span>{c.name}</span>
                      <Badge variant="outline" className="tabular-nums">{c.mentions}</Badge>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Call Duration</CardTitle>
                <CardDescription>Average conversation length per day (overall {formatDuration(o.average_duration_seconds)})</CardDescription>
              </CardHeader>
              <CardContent>
                {durationData.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No durations recorded in this period</p>
                ) : (
                  <ChartContainer config={durationConfig} className="aspect-auto h-[180px] w-full">
                    <LineChart data={durationData}>
                      <CartesianGrid vertical={false} />
                      <XAxis dataKey="date" tickLine={false} axisLine={false} tickFormatter={shortDay} minTickGap={24} />
                      <YAxis tickLine={false} axisLine={false} width={32} />
                      <ChartTooltip content={<ChartTooltipContent labelFormatter={(v) => shortDay(String(v))} />} />
                      <Line type="monotone" dataKey="minutes" stroke="var(--color-minutes)" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ChartContainer>
                )}
              </CardContent>
            </Card>
          </>
        ) : null}
      </div>
    </AppShell>
  );
}
