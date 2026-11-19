"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Search, Users } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { apiErrorMessage } from "@/lib/api/errors";
import { PIPELINE_STAGES, salesApi, type SalesLead } from "@/lib/api/sales";
import { formatDate, humanize } from "@/lib/format";
import { ErrorState, PageLoading } from "@/components/common/ErrorState";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { InputGroup, InputGroupAddon, InputGroupInput } from "@/components/ui/input-group";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const SCORE_FILTERS = [
  { value: "any", label: "Any score" },
  { value: "50", label: "Score 50+" },
  { value: "70", label: "Score 70+" },
  { value: "80", label: "Score 80+" },
];

function IntentBadge({ intent }: { intent: string | null }) {
  if (!intent) return <span className="text-muted-foreground">-</span>;
  return (
    <Badge variant={intent === "high" ? "secondary" : intent === "low" ? "destructive" : "outline"} className="capitalize">
      {intent}
    </Badge>
  );
}

function HealthBadge({ health }: { health: string | null }) {
  if (!health) return <span className="text-muted-foreground">-</span>;
  return (
    <Badge variant={health === "critical" ? "destructive" : "outline"} className="capitalize">
      <span className={health === "healthy" ? "size-1.5 rounded-full bg-emerald-500" : health === "at_risk" ? "size-1.5 rounded-full bg-amber-500" : "size-1.5 rounded-full bg-destructive"} />
      {humanize(health)}
    </Badge>
  );
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<SalesLead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [minScore, setMinScore] = useState("any");
  const [intent, setIntent] = useState("all");
  const [health, setHealth] = useState("all");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setLeads(await salesApi.pipeline({
        search: search.trim() || undefined,
        min_score: minScore === "any" ? undefined : Number(minScore),
        purchase_intent: intent === "all" ? undefined : intent,
        deal_health: health === "all" ? undefined : health,
      }));
    } catch (err) {
      setError(apiErrorMessage(err, "Leads couldn't be loaded."));
    } finally {
      setLoading(false);
    }
  }, [search, minScore, intent, health]);

  useEffect(() => {
    const timer = setTimeout(load, search ? 300 : 0);
    return () => clearTimeout(timer);
  }, [load, search]);

  const changeStage = async (lead: SalesLead, stage: string) => {
    try {
      const updated = await salesApi.setStage(lead.conversation_id, stage);
      setLeads((all) => all.map((l) => (l.conversation_id === lead.conversation_id ? updated : l)));
      toast.success(`Moved to ${humanize(stage)}`);
    } catch (err) {
      toast.error(apiErrorMessage(err, "Couldn't change the stage"));
    }
  };

  const highIntent = leads.filter((l) => l.purchase_intent === "high").length;
  const atRisk = leads.filter((l) => l.deal_health === "at_risk" || l.deal_health === "critical").length;

  return (
    <AppShell title="Leads" subtitle="High-intent sales prospects and lead scoring dashboard">
      <div className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card size="sm">
            <CardHeader>
              <CardDescription>Leads</CardDescription>
              <CardTitle className="text-2xl tabular-nums">{leads.length}</CardTitle>
            </CardHeader>
          </Card>
          <Card size="sm">
            <CardHeader>
              <CardDescription>High purchase intent</CardDescription>
              <CardTitle className="text-2xl tabular-nums">{highIntent}</CardTitle>
            </CardHeader>
          </Card>
          <Card size="sm">
            <CardHeader>
              <CardDescription>At risk or critical</CardDescription>
              <CardTitle className="text-2xl tabular-nums">{atRisk}</CardTitle>
            </CardHeader>
          </Card>
        </div>

        <Card>
          <CardHeader className="gap-3">
            <CardTitle>Leads directory</CardTitle>
            <CardDescription>
              Every sales conversation the AI analyzed. Scores, intent and deal health come from the call;
              change the stage when a deal moves.
            </CardDescription>
            <div className="flex flex-wrap items-center gap-2">
              <InputGroup className="w-full sm:w-64">
                <InputGroupAddon>
                  <Search />
                </InputGroupAddon>
                <InputGroupInput placeholder="Search leads" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search leads" />
              </InputGroup>
              <Select value={minScore} onValueChange={setMinScore}>
                <SelectTrigger size="sm" aria-label="Minimum lead score"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {SCORE_FILTERS.map((f) => <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={intent} onValueChange={setIntent}>
                <SelectTrigger size="sm" aria-label="Purchase intent"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Any intent</SelectItem>
                  <SelectItem value="high">High intent</SelectItem>
                  <SelectItem value="medium">Medium intent</SelectItem>
                  <SelectItem value="low">Low intent</SelectItem>
                </SelectContent>
              </Select>
              <Select value={health} onValueChange={setHealth}>
                <SelectTrigger size="sm" aria-label="Deal health"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Any deal health</SelectItem>
                  <SelectItem value="healthy">Healthy</SelectItem>
                  <SelectItem value="at_risk">At risk</SelectItem>
                  <SelectItem value="critical">Critical</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardHeader>
          <CardContent>
            {loading && leads.length === 0 ? (
              <PageLoading />
            ) : error ? (
              <ErrorState message={error} onRetry={load} />
            ) : leads.length === 0 ? (
              <Empty>
                <EmptyHeader>
                  <EmptyMedia variant="icon"><Users /></EmptyMedia>
                  <EmptyTitle>No leads match</EmptyTitle>
                  <EmptyDescription>Leads appear after a sales conversation is analyzed. Try clearing the filters.</EmptyDescription>
                </EmptyHeader>
              </Empty>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Lead</TableHead>
                    <TableHead className="w-32">Score</TableHead>
                    <TableHead>Intent</TableHead>
                    <TableHead>Stage</TableHead>
                    <TableHead>Deal health</TableHead>
                    <TableHead>Next action</TableHead>
                    <TableHead>Last activity</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {leads.map((lead) => (
                    <TableRow key={lead.conversation_id}>
                      <TableCell className="max-w-64">
                        <Link href={`/conversations/${lead.conversation_id}`} className="font-medium hover:underline line-clamp-2 whitespace-normal">
                          {lead.title}
                        </Link>
                        <span className="text-xs text-muted-foreground">
                          {[lead.owner_name, lead.budget_range && `Budget ${lead.budget_range}`, lead.decision_maker_present && "Decision maker on call"]
                            .filter(Boolean).join(" · ")}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span className="w-7 font-semibold tabular-nums">{lead.lead_score ?? "-"}</span>
                          <Progress value={lead.lead_score ?? 0} className="h-1.5" />
                        </div>
                      </TableCell>
                      <TableCell><IntentBadge intent={lead.purchase_intent} /></TableCell>
                      <TableCell>
                        <Select value={lead.pipeline_stage ?? undefined} onValueChange={(stage) => changeStage(lead, stage)}>
                          <SelectTrigger size="sm" aria-label={`Stage for ${lead.title}`}>
                            <SelectValue placeholder="Set stage" />
                          </SelectTrigger>
                          <SelectContent>
                            {PIPELINE_STAGES.map((stage) => <SelectItem key={stage} value={stage}>{humanize(stage)}</SelectItem>)}
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell><HealthBadge health={lead.deal_health} /></TableCell>
                      <TableCell className="max-w-72 whitespace-normal text-sm text-muted-foreground">
                        {lead.next_action ?? "-"}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{formatDate(lead.last_activity_at)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
