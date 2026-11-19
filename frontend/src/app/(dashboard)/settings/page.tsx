"use client";

import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Cpu, History, Settings } from "lucide-react";
import { toast } from "sonner";
import { apiErrorMessage } from "@/lib/api/errors";
import { systemApi, type AiSettings, type AuditLogItem } from "@/lib/api/system";
import { usersApi, type Preferences } from "@/lib/api/users";
import { useRole } from "@/lib/stores/authStore";
import { formatDateTime, humanize } from "@/lib/format";
import { ErrorState, PageLoading } from "@/components/common/ErrorState";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldContent, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const preferences: { id: keyof Preferences; title: string; description: string }[] = [
  {
    id: "auto_action_items",
    title: "Automatic Action Item Extraction",
    description: "Automatically extract tasks from uploaded call recordings using LLM pipeline",
  },
  {
    id: "lead_intent_alerts",
    title: "Real-Time Lead Intent Alerts",
    description: "Receive notifications when a high-intent lead score (80+) is detected",
  },
  {
    id: "pbx_auto_sync",
    title: "TalkWisely Cloud PBX Auto-Sync",
    description: "Import new calls from the TalkWisely PBX adapter every 15 minutes",
  },
];

function describeDetails(log: AuditLogItem): string {
  const entries = Object.entries(log.details ?? {}).filter(([, v]) => v !== null && typeof v !== "object");
  return entries.slice(0, 3).map(([k, v]) => `${humanize(k)}: ${String(v)}`).join(", ");
}

export default function SettingsPage() {
  const role = useRole();
  const [prefs, setPrefs] = useState<Preferences | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState<keyof Preferences | null>(null);
  const [ai, setAi] = useState<AiSettings | null>(null);
  const [logs, setLogs] = useState<AuditLogItem[] | null>(null);

  const load = useCallback(async () => {
    try {
      const saved = await usersApi.preferences();
      setPrefs(saved);
      setError("");
    } catch (err) {
      setError(apiErrorMessage(err, "Your preferences couldn't be loaded."));
    }
    if (role !== "agent") systemApi.aiSettings().then(setAi).catch(() => setAi(null));
    if (role === "admin") systemApi.auditLogs(30).then(setLogs).catch(() => setLogs(null));
  }, [role]);

  useEffect(() => {
    load();
  }, [load]);

  const toggle = async (id: keyof Preferences, value: boolean) => {
    if (!prefs) return;
    const previous = prefs;
    setPrefs({ ...prefs, [id]: value });
    setSaving(id);
    try {
      setPrefs(await usersApi.savePreferences({ [id]: value }));
      toast.success("Preference saved");
    } catch (err) {
      setPrefs(previous);
      toast.error(apiErrorMessage(err, "Couldn't save the preference"));
    } finally {
      setSaving(null);
    }
  };

  return (
    <AppShell title="Settings" subtitle="System preferences, notification thresholds & AI model configurations">
      <div className="space-y-6">
        <Card className="max-w-3xl">
          <CardHeader className="border-b">
            <CardTitle className="flex items-center gap-2">
              <Settings className="size-5" />
              Application Preferences
            </CardTitle>
            <CardDescription>Saved to your account and applied to recordings you upload.</CardDescription>
          </CardHeader>

          <CardContent>
            {error ? (
              <ErrorState message={error} onRetry={() => { setError(""); load(); }} />
            ) : !prefs ? (
              <PageLoading />
            ) : (
              <FieldGroup className="gap-4">
                {preferences.map((pref) => (
                  <FieldLabel key={pref.id} htmlFor={pref.id}>
                    <Field orientation="horizontal">
                      <FieldContent>
                        <span className="text-sm font-medium">{pref.title}</span>
                        <FieldDescription className="text-xs">{pref.description}</FieldDescription>
                      </FieldContent>
                      <Switch
                        id={pref.id}
                        checked={prefs[pref.id]}
                        disabled={saving === pref.id}
                        onCheckedChange={(v) => toggle(pref.id, v)}
                      />
                    </Field>
                  </FieldLabel>
                ))}
              </FieldGroup>
            )}
          </CardContent>
        </Card>

        {ai && (
          <Card className="max-w-3xl">
            <CardHeader className="border-b">
              <CardTitle className="flex items-center gap-2">
                <Cpu className="size-5" />
                AI Model Configuration
              </CardTitle>
              <CardDescription>{ai.how_to_change} API keys stay in environment variables and are never shown here.</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Component</TableHead>
                    <TableHead>Provider</TableHead>
                    <TableHead>Model</TableHead>
                    <TableHead>Used for</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {ai.providers.map((p) => (
                    <TableRow key={p.kind}>
                      <TableCell className="font-medium">{p.kind}</TableCell>
                      <TableCell>
                        {p.is_mock ? <Badge variant="outline">Mock (canned output)</Badge> : <Badge variant="secondary">{p.provider}</Badge>}
                      </TableCell>
                      <TableCell className="text-muted-foreground">{p.model ?? "-"}</TableCell>
                      <TableCell className="whitespace-normal text-xs text-muted-foreground">{p.note}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <p className="mt-3 text-xs text-muted-foreground">
                Background jobs run {ai.task_queue === "celery" ? "on Celery workers" : "inside the API process"}.
              </p>
            </CardContent>
          </Card>
        )}

        {role === "admin" && logs && (
          <Card>
            <CardHeader className="border-b">
              <CardTitle className="flex items-center gap-2">
                <History className="size-5" />
                Audit Log
              </CardTitle>
              <CardDescription>The 30 most recent sign-ins, uploads, deletions, approvals and setting changes.</CardDescription>
            </CardHeader>
            <CardContent>
              {logs.length === 0 ? (
                <p className="text-sm text-muted-foreground">No activity recorded yet.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>When</TableHead>
                      <TableHead>Who</TableHead>
                      <TableHead>Action</TableHead>
                      <TableHead>Details</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.map((log) => (
                      <TableRow key={log.id}>
                        <TableCell className="text-xs text-muted-foreground">{formatDateTime(log.created_at)}</TableCell>
                        <TableCell className="text-sm">{log.user_name ?? "System"}</TableCell>
                        <TableCell><Badge variant="outline">{humanize(log.action)}</Badge></TableCell>
                        <TableCell className="max-w-96 truncate text-xs text-muted-foreground">{describeDetails(log)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
