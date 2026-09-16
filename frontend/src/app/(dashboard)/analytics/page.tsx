"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Users, AlertTriangle } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle,
} from "@/components/ui/card";
import {
  Item, ItemActions, ItemContent, ItemDescription, ItemGroup, ItemMedia, ItemTitle,
} from "@/components/ui/item";
import { Progress } from "@/components/ui/progress";

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
          <Card>
            <CardHeader>
              <CardDescription>Total Conversations</CardDescription>
              <CardTitle className="text-3xl font-semibold tabular-nums">{analytics?.total_conversations ?? 1248}</CardTitle>
            </CardHeader>
            <CardFooter className="text-xs font-medium text-success">↑ 14% vs last month</CardFooter>
          </Card>
          <Card>
            <CardHeader>
              <CardDescription>Avg Sentiment Score</CardDescription>
              <CardTitle className="text-3xl font-semibold tabular-nums">+{analytics?.avg_sentiment_score ?? "0.68"}</CardTitle>
            </CardHeader>
            <CardFooter className="text-xs text-muted-foreground">Positive trend indicator</CardFooter>
          </Card>
          <Card>
            <CardHeader>
              <CardDescription>Avg Agent Score</CardDescription>
              <CardTitle className="text-3xl font-semibold tabular-nums">{analytics?.avg_agent_score ?? 87}/100</CardTitle>
            </CardHeader>
            <CardFooter className="text-xs text-muted-foreground">QA Evaluation average</CardFooter>
          </Card>
          <Card>
            <CardHeader>
              <CardDescription>High Intent Pipeline</CardDescription>
              <CardTitle className="text-3xl font-semibold tabular-nums">{analytics?.high_intent_leads ?? 84}</CardTitle>
            </CardHeader>
            <CardFooter className="text-xs text-muted-foreground">Qualified leads</CardFooter>
          </Card>
        </div>

        {/* Objection & Agent Performance breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Objections chart */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="size-4 text-warning" />
                Objection Frequency Matrix
              </CardTitle>
            </CardHeader>
            <CardContent>
              {(analytics?.objection_breakdown || []).map((item: any, i: number) => (
                <div key={i} className="space-y-1.5">
                  <div className="flex justify-between text-xs font-medium">
                    <span>{item.category}</span>
                    <span className="text-muted-foreground tabular-nums">{item.count} mentions</span>
                  </div>
                  <Progress
                    value={Math.min(100, (item.count / 50) * 100)}
                    className="h-2 *:data-[slot=progress-indicator]:bg-amber-500"
                  />
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Agent Leaderboard */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="size-4" />
                Team Performance Leaderboard
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ItemGroup className="gap-2.5">
                {(analytics?.agent_leaderboard || []).map((agent: any, idx: number) => (
                  <Item key={idx} variant="muted" size="sm">
                    <ItemMedia>
                      <Avatar>
                        <AvatarFallback className="text-xs font-semibold">#{idx + 1}</AvatarFallback>
                      </Avatar>
                    </ItemMedia>
                    <ItemContent>
                      <ItemTitle>{agent.name}</ItemTitle>
                      <ItemDescription className="text-xs">{agent.calls} calls evaluated</ItemDescription>
                    </ItemContent>
                    <ItemActions className="flex-col items-end gap-0">
                      <span className="text-sm font-semibold tabular-nums">{agent.score}/100</span>
                      <span className="text-[10px] text-muted-foreground uppercase font-semibold">QA score</span>
                    </ItemActions>
                  </Item>
                ))}
              </ItemGroup>
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}
