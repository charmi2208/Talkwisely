"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Check, Database, Pencil, X } from "lucide-react";
import { crmApi, type CRMChange, type CRMProposal } from "@/lib/api/crm";
import { apiErrorMessage } from "@/lib/api/errors";
import { parseApiDate } from "@/lib/dates";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const fieldLabel = (key: string) => key.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

const show = (value: unknown) => {
  if (value === null || value === undefined || value === "") return "Not set";
  const text = String(value);
  return text.charAt(0).toUpperCase() + text.slice(1);
};

// Changes arrive either as {from, to} pairs or as a plain new value
function split(change: CRMChange): { from: unknown; to: unknown } {
  if (change && typeof change === "object" && ("to" in change || "from" in change)) {
    return { from: change.from, to: change.to };
  }
  return { from: undefined, to: change };
}

function withEditedValue(change: CRMChange, raw: string): CRMChange {
  const { from, to } = split(change);
  const value = typeof to === "number" && raw.trim() !== "" && !Number.isNaN(Number(raw)) ? Number(raw) : raw;
  return change && typeof change === "object" ? { from, to: value } : value;
}

function StatusBadge({ proposal }: { proposal: CRMProposal }) {
  if (proposal.status === "applied") return <Badge variant="secondary"><Check data-icon="inline-start" className="text-success" />Applied</Badge>;
  if (proposal.status === "rejected") return <Badge variant="outline"><X data-icon="inline-start" />Rejected</Badge>;
  return <Badge variant="outline">Awaiting approval</Badge>;
}

function ProposalCard({ proposal, onChange }: { proposal: CRMProposal; onChange: (p: CRMProposal) => void }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);
  const entries = Object.entries(proposal.proposed_changes);
  const isPending = proposal.status === "pending";
  const providerLabel = proposal.crm_provider === "mock" ? "Mock CRM" : proposal.crm_provider;

  const startEditing = () => {
    setDraft(Object.fromEntries(entries.map(([k, v]) => [k, split(v).to == null ? "" : String(split(v).to)])));
    setEditing(true);
  };

  const approve = async () => {
    setBusy("approve");
    try {
      const edited = editing
        ? Object.fromEntries(entries.map(([k, v]) => [k, withEditedValue(v, draft[k] ?? "")]))
        : undefined;
      onChange(await crmApi.approve(proposal.id, edited));
      setEditing(false);
      toast.success(`CRM updated in ${providerLabel}`);
    } catch (err) {
      toast.error(apiErrorMessage(err, "Couldn't apply the CRM update"));
    } finally {
      setBusy(null);
    }
  };

  const reject = async () => {
    setBusy("reject");
    try {
      onChange(await crmApi.reject(proposal.id));
      toast.success("Proposal rejected. Nothing was sent to the CRM.");
    } catch (err) {
      toast.error(apiErrorMessage(err, "Couldn't reject the proposal"));
    } finally {
      setBusy(null);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="capitalize">{proposal.crm_entity_type} update</CardTitle>
        <CardDescription>
          {proposal.status === "applied" && proposal.applied_at
            ? `Approved and written to ${providerLabel} on ${parseApiDate(proposal.applied_at).toLocaleString()}.`
            : proposal.status === "rejected"
              ? `Rejected. Nothing was written to ${providerLabel}.`
              : `AI-proposed changes for ${providerLabel}. Nothing is written until you approve.`}
        </CardDescription>
        <CardAction>
          <StatusBadge proposal={proposal} />
        </CardAction>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Field</TableHead>
              <TableHead>Current</TableHead>
              <TableHead>{isPending ? "Proposed" : "New value"}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {entries.map(([key, change]) => {
              const { from, to } = split(change);
              return (
                <TableRow key={key}>
                  <TableCell className="font-medium">{fieldLabel(key)}</TableCell>
                  <TableCell className="text-muted-foreground">{from === undefined ? "—" : show(from)}</TableCell>
                  <TableCell className="whitespace-normal">
                    {editing ? (
                      <Input
                        aria-label={`New value for ${fieldLabel(key)}`}
                        value={draft[key] ?? ""}
                        onChange={(e) => setDraft((d) => ({ ...d, [key]: e.target.value }))}
                        className="h-8"
                      />
                    ) : (
                      <span>{show(to)}</span>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
      {isPending && (
        <CardFooter className="border-t justify-end gap-2">
          {editing ? (
            <Button variant="ghost" size="sm" onClick={() => setEditing(false)} disabled={!!busy}>
              Cancel edits
            </Button>
          ) : (
            <Button variant="ghost" size="sm" onClick={startEditing} disabled={!!busy}>
              <Pencil data-icon="inline-start" />
              Edit
            </Button>
          )}
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="outline" size="sm" disabled={!!busy}>
                {busy === "reject" ? <Spinner data-icon="inline-start" /> : <X data-icon="inline-start" />}
                Reject
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Reject this CRM update?</AlertDialogTitle>
                <AlertDialogDescription>
                  The proposed changes will be discarded and nothing will be sent to {providerLabel}.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction variant="destructive" onClick={reject}>Reject update</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
          <Button size="sm" onClick={approve} disabled={!!busy}>
            {busy === "approve" ? <Spinner data-icon="inline-start" /> : <Check data-icon="inline-start" />}
            {editing ? "Approve edited update" : "Approve & update CRM"}
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}

export function CrmProposalsPanel({ conversationId }: { conversationId: string }) {
  const [proposals, setProposals] = useState<CRMProposal[] | null>(null);

  useEffect(() => {
    let ignore = false;
    crmApi
      .list({ conversation_id: conversationId })
      .then((data) => { if (!ignore) setProposals(data); })
      .catch(() => {
        if (ignore) return;
        setProposals([]);
        toast.error("Couldn't load CRM proposals");
      });
    return () => { ignore = true; };
  }, [conversationId]);

  if (proposals === null) {
    return (
      <div className="flex justify-center py-12">
        <Spinner className="size-6" />
      </div>
    );
  }

  if (proposals.length === 0) {
    return (
      <Empty className="border">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <Database />
          </EmptyMedia>
          <EmptyTitle>No CRM updates proposed</EmptyTitle>
          <EmptyDescription>
            The AI didn&apos;t find anything in this conversation that should change your CRM records.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  return (
    <div className="space-y-4">
      {proposals.map((p) => (
        <ProposalCard
          key={p.id}
          proposal={p}
          onChange={(updated) => setProposals((prev) => prev?.map((x) => (x.id === updated.id ? updated : x)) ?? null)}
        />
      ))}
    </div>
  );
}
