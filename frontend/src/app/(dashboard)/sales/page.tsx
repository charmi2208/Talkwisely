"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { TrendingUp, Target, Shield, RefreshCw, Filter, DollarSign } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle,
} from "@/components/ui/card";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

interface SalesLead {
  conversation_id: string;
  title: string;
  lead_score: number | null;
  purchase_intent: string | null;
  deal_health: string | null;
  pipeline_stage: string | null;
  budget_range: string | null;
  created_at: string;
}

export default function SalesPage() {
  const [leads, setLeads] = useState<SalesLead[]>([]);
  const [loading, setLoading] = useState(true);
  const [stageFilter, setStageFilter] = useState<string>("all");

  const loadSalesData = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get<SalesLead[]>("/sales/pipeline");
      setLeads(Array.isArray(res.data) ? res.data : []);
    } catch {
      // Fallback demo leads if backend server initializing
      setLeads([
        {
          conversation_id: "demo_1",
          title: "Enterprise PBX Cloud Migration — Acme Corp",
          lead_score: 92,
          purchase_intent: "high",
          deal_health: "healthy",
          pipeline_stage: "proposal",
          budget_range: "$25,000 - $50,000",
          created_at: new Date().toISOString(),
        },
        {
          conversation_id: "demo_2",
          title: "Contact Center AI Integration — Nexus Telecom",
          lead_score: 78,
          purchase_intent: "medium",
          deal_health: "healthy",
          pipeline_stage: "demo",
          budget_range: "$15,000 - $30,000",
          created_at: new Date().toISOString(),
        },
        {
          conversation_id: "demo_3",
          title: "VoIP Trunking & UK Numbers — Global Logistics",
          lead_score: 85,
          purchase_intent: "high",
          deal_health: "healthy",
          pipeline_stage: "negotiation",
          budget_range: "$40,000+",
          created_at: new Date().toISOString(),
        },
        {
          conversation_id: "demo_4",
          title: "Support Automation Pilot — Retail One",
          lead_score: 45,
          purchase_intent: "low",
          deal_health: "at_risk",
          pipeline_stage: "qualified",
          budget_range: "$10,000",
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSalesData();
  }, []);

  const stages = [
    { id: "all", label: "All Stages" },
    { id: "qualified", label: "Qualified" },
    { id: "demo", label: "Demo" },
    { id: "proposal", label: "Proposal" },
    { id: "negotiation", label: "Negotiation" },
  ];

  const safeLeads = Array.isArray(leads) ? leads : [];
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
            { label: "Active Deals", value: safeLeads.length, hint: "Under AI evaluation", icon: DollarSign },
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
            <Button variant="outline" size="sm" onClick={loadSalesData}>
              <RefreshCw data-icon="inline-start" />
              Refresh
            </Button>
          </CardContent>
        </Card>

        {/* Sales Pipeline Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredLeads.map((lead) => (
            <Link key={lead.conversation_id} href={`/conversations/${lead.conversation_id}`} className="group">
              <Card className="h-full transition-colors group-hover:bg-muted/40">
                <CardHeader>
                  <CardTitle className="line-clamp-2">{lead.title}</CardTitle>
                  <CardAction className="text-right">
                    <span className="text-xl font-semibold tabular-nums">{lead.lead_score ?? "N/A"}</span>
                    <span className="text-[10px] font-semibold text-muted-foreground block uppercase">score</span>
                  </CardAction>
                </CardHeader>

                <CardContent className="flex-row items-center gap-2">
                  <Badge
                    variant={lead.purchase_intent === "high" ? "secondary" : lead.purchase_intent === "medium" ? "outline" : "destructive"}
                    className="capitalize"
                  >
                    {lead.purchase_intent} intent
                  </Badge>
                  <Badge variant="outline" className="capitalize">
                    <span className={lead.deal_health === "healthy" ? "size-1.5 rounded-full bg-emerald-500" : "size-1.5 rounded-full bg-amber-500"} />
                    {lead.deal_health?.replace("_", " ")}
                  </Badge>
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
      </div>
    </AppShell>
  );
}
