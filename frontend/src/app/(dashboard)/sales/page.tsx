"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { TrendingUp, Target, Shield, RefreshCw, Filter, DollarSign } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import Link from "next/link";
import { clsx } from "clsx";

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
          <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-500">High Intent Leads</span>
              <div className="p-2 rounded-lg bg-emerald-50 text-emerald-600 border border-emerald-100">
                <Target className="w-4 h-4" />
              </div>
            </div>
            <p className="text-3xl font-extrabold text-slate-900">{highIntentCount}</p>
            <p className="text-xs text-slate-400 mt-0.5">Ready for closing</p>
          </div>

          <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-500">Avg Lead Score</span>
              <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-100">
                <TrendingUp className="w-4 h-4" />
              </div>
            </div>
            <p className="text-3xl font-extrabold text-indigo-600">{avgLeadScore}</p>
            <p className="text-xs text-slate-400 mt-0.5">Out of 100 max score</p>
          </div>

          <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-500">Active Deals</span>
              <div className="p-2 rounded-lg bg-purple-50 text-purple-600 border border-purple-100">
                <DollarSign className="w-4 h-4" />
              </div>
            </div>
            <p className="text-3xl font-extrabold text-slate-900">{safeLeads.length}</p>
            <p className="text-xs text-slate-400 mt-0.5">Under AI evaluation</p>
          </div>

          <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-500">Healthy Deals</span>
              <div className="p-2 rounded-lg bg-amber-50 text-amber-600 border border-amber-100">
                <Shield className="w-4 h-4" />
              </div>
            </div>
            <p className="text-3xl font-extrabold text-amber-600">
              {safeLeads.filter((l) => l.deal_health === "healthy").length}
            </p>
            <p className="text-xs text-slate-400 mt-0.5">Low risk indicator</p>
          </div>
        </div>

        {/* Filter bar */}
        <div className="flex items-center justify-between gap-4 glass-card p-4">
          <div className="flex items-center gap-2 overflow-x-auto">
            <Filter className="w-4 h-4 text-slate-400 mr-1 flex-shrink-0" />
            {stages.map((st) => (
              <button
                key={st.id}
                onClick={() => setStageFilter(st.id)}
                className={clsx(
                  "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex-shrink-0",
                  stageFilter === st.id
                    ? "bg-indigo-600 text-white shadow-xs"
                    : "bg-slate-100 text-slate-600 hover:text-slate-900 hover:bg-slate-200"
                )}
              >
                {st.label}
              </button>
            ))}
          </div>
          <button
            onClick={loadSalesData}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white border border-slate-300 hover:bg-slate-50 text-xs font-semibold text-slate-700 transition-colors shadow-xs"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
        </div>

        {/* Sales Pipeline Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredLeads.map((lead) => (
            <Link key={lead.conversation_id} href={`/conversations/${lead.conversation_id}`} className="group">
              <div className="glass-card p-5 hover:border-slate-300 transition-all space-y-4">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-sm font-bold text-slate-900 group-hover:text-indigo-600 transition-colors line-clamp-2">
                    {lead.title}
                  </h3>
                  <div className="text-right flex-shrink-0">
                    <span className="text-xl font-extrabold text-indigo-600">{lead.lead_score ?? "N/A"}</span>
                    <span className="text-[10px] font-semibold text-slate-400 block uppercase">score</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className={clsx("text-xs px-2.5 py-0.5 rounded-full font-semibold capitalize border",
                    lead.purchase_intent === "high" ? "badge-positive" :
                    lead.purchase_intent === "medium" ? "badge-neutral" : "badge-negative"
                  )}>
                    {lead.purchase_intent} intent
                  </span>

                  <span className={clsx("text-xs px-2.5 py-0.5 rounded-full font-semibold capitalize border",
                    lead.deal_health === "healthy" ? "border-emerald-200 text-emerald-700 bg-emerald-50" : "border-amber-200 text-amber-700 bg-amber-50"
                  )}>
                    {lead.deal_health?.replace("_", " ")}
                  </span>
                </div>

                {lead.budget_range && (
                  <div className="flex items-center gap-2 text-xs text-slate-500 pt-2 border-t border-slate-100">
                    <DollarSign className="w-3.5 h-3.5 text-slate-400" />
                    <span>Budget: <strong className="text-slate-800 font-semibold">{lead.budget_range}</strong></span>
                  </div>
                )}
              </div>
            </Link>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
