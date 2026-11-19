"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { TrendingUp, Target, Shield, RefreshCw, Filter, DollarSign } from "lucide-react";
import Link from "next/link";
import { apiErrorMessage } from "@/lib/api/errors";
import { PIPELINE_STAGES, salesApi, type SalesLead } from "@/lib/api/sales";
import { formatDate, humanize } from "@/lib/format";
import { ErrorState, PageLoading } from "@/components/common/ErrorState";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle,
} from "@/components/ui/card";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

export default function SalesPage() {
  const [leads, setLeads] = useState<SalesLead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [stageFilter, setStageFilter] = useState<string>("all");

  const loadSalesData = async () => {
    try {
      const list = await salesApi.pipeline();
      setLeads(list);
      setError("");
    } catch (err) {
      setError(apiErrorMessage(err, "Sales data couldn't be loaded."));
    } finally {
      setLoading(false);
    }
  };

  const reload = () => {
    setLoading(true);
    setError("");
    loadSalesData();
  };

  useEffect(() => {
    loadSalesData();
  }, []);

  const safeLeads = Array.isArray(leads) ? leads : [];
  const stages = [
    { id: "all", label: `All stages (${safeLeads.length})` },
    ...PIPELINE_STAGES.map((stage) => ({
      id: stage,
      label: `${humanize(stage)} (${safeLeads.filter((l) => l.pipeline_stage === stage).length})`,
    })),
  ];
  const filteredLeads = stageFilter === "all" ? safeLeads : safeLeads.filter((l) => l.pipeline_stage === stageFilter);

  const highIntentCount = safeLeads.filter((l) => l.purchase_intent === "high").length;
  const avgLeadScore = safeLeads.length > 0 ? Math.round(safeLeads.reduce((acc, l) => acc + (l.lead_score || 0), 0) / safeLeads.length) : 0;

  return (
    <AppShell title="Sales Intelligence" subtitle="Conversation-driven sales opportunities, lead scores & deal health">
      <div className="space-y-6">
        {/* Metric cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[
            { label: "High Intent Leads", value: highIntentCount, hint: "Ready for closing", icon: Target },
            { label: "Avg Lead Score", value: avgLeadScore, hint: "Out of 100 max score", icon: TrendingUp },
            { label: "Active Deals", value: safeLeads.filter((l) => l.pipeline_stage !== "won" && l.pipeline_stage !== "lost").length, hint: "Not yet won or lost", icon: DollarSign },
            { label: "Healthy Deals", value: safeLeads.filter((l) => l.deal_health === "healthy").length, hint: "Low risk indicator", icon: Shield },
          ].map((metric) => (
            <Card key={metric.label}>
              <CardHeader>
                <CardDescription>{metric.label}</CardDescription>
                <CardTitle className="text-3xl font-semibold tabular-nums">{metric.value}</CardTitle>
                <CardAction>
                  <metric.icon className="size-4 text-muted-foreground" />
                </CardAction>
              </CardHeader>
              <CardFooter className="text-xs text-muted-foreground">{metric.hint}</CardFooter>
            </Card>
          ))}
        </div>

        {/* Filter bar */}
        <Card size="sm">
          <CardContent className="flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2 overflow-x-auto">
              <Filter className="size-4 text-muted-foreground mr-1 shrink-0" />
              <ToggleGroup
                type="single"
                variant="outline"
                size="sm"
                value={stageFilter}
                onValueChange={(v) => v && setStageFilter(v)}
              >
                {stages.map((st) => (
                  <ToggleGroupItem key={st.id} value={st.id} className="text-xs">
                    {st.label}
                  </ToggleGroupItem>
                ))}
              </ToggleGroup>
            </div>
            <Button variant="outline" size="sm" onClick={reload}>
              <RefreshCw data-icon="inline-start" />
              Refresh
            </Button>
          </CardContent>
        </Card>

        {/* Sales Pipeline Grid */}
        {loading && safeLeads.length === 0 ? (
          <PageLoading />
        ) : error ? (
          <ErrorState message={error} onRetry={reload} />
        ) : filteredLeads.length === 0 ? (
          <Empty className="border bg-card">
            <EmptyHeader>
              <EmptyMedia variant="icon"><Target /></EmptyMedia>
              <EmptyTitle>No deals in this stage</EmptyTitle>
              <EmptyDescription>Deals appear here after sales conversations are analyzed.</EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredLeads.map((lead) => (
            <Link key={lead.conversation_id} href={`/conversations/${lead.conversation_id}`} className="group">
              <Card className="h-full transition-colors group-hover:bg-muted/40">
                <CardHeader>
                  <CardTitle className="line-clamp-2">{lead.title}</CardTitle>
                  <CardDescription className="text-xs">
                    {humanize(lead.pipeline_stage) || "No stage"} · last activity {formatDate(lead.last_activity_at)}
                  </CardDescription>
                  <CardAction className="text-right">
                    <span className="text-xl font-semibold tabular-nums">{lead.lead_score ?? "N/A"}</span>
                    <span className="text-[10px] font-semibold text-muted-foreground block uppercase">score</span>
                  </CardAction>
                </CardHeader>

                <CardContent className="flex flex-col gap-3">
                  <div className="flex flex-row flex-wrap items-center gap-2">
                    <Badge
                      variant={lead.purchase_intent === "high" ? "secondary" : lead.purchase_intent === "medium" ? "outline" : "destructive"}
                      className="capitalize"
                    >
                      {lead.purchase_intent ?? "unknown"} intent
                    </Badge>
                    {lead.deal_health && (
                      <Badge variant="outline" className="capitalize">
                        <span className={lead.deal_health === "healthy" ? "size-1.5 rounded-full bg-emerald-500" : "size-1.5 rounded-full bg-amber-500"} />
                        {lead.deal_health.replace("_", " ")}
                      </Badge>
                    )}
                  </div>
                  {lead.next_action && (
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      <span className="font-medium text-foreground">Next: </span>{lead.next_action}
                    </p>
                  )}
                </CardContent>

                {lead.budget_range && (
                  <CardFooter className="border-t gap-2 text-xs text-muted-foreground">
                    <DollarSign className="size-3.5" />
                    <span>Budget: <strong className="text-foreground font-semibold">{lead.budget_range}</strong></span>
                  </CardFooter>
                )}
              </Card>
            </Link>
          ))}
        </div>
        )}
      </div>
    </AppShell>
  );
}
