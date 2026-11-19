"use client";

import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Phone, Database, Calendar, Mail, RefreshCw, Zap, Settings2, CircleSlash, FlaskConical, Video } from "lucide-react";
import { toast } from "sonner";
import { apiErrorMessage } from "@/lib/api/errors";
import { integrationsApi, type Integration } from "@/lib/api/integrations";
import { useRole } from "@/lib/stores/authStore";
import { formatDateTime } from "@/lib/format";
import { ErrorState, PageLoading } from "@/components/common/ErrorState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle,
} from "@/components/ui/card";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldContent, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { Switch } from "@/components/ui/switch";

const icons: Record<string, React.ElementType> = {
  talkwisely: Phone,
  meetings: Video,
  crm: Database,
  calendar: Calendar,
  email: Mail,
};

interface Draft {
  is_enabled: boolean;
  provider: string;
  config: Record<string, string | number>;
}

export default function IntegrationsPage() {
  const role = useRole();
  const isAdmin = role === "admin";
  const canOperate = role !== "agent";
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [importing, setImporting] = useState<string | null>(null);
  const [editing, setEditing] = useState<Integration | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const list = await integrationsApi.list();
      setIntegrations(list);
      setError("");
    } catch (err) {
      setError(apiErrorMessage(err, "Integrations couldn't be loaded."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const pbx = integrations.find((i) => i.key === "talkwisely");

  const handleSync = async () => {
    setSyncing(true);
    try {
      const result = await integrationsApi.syncPbx();
      toast.success(result.message);
      load();
    } catch (err) {
      toast.error(apiErrorMessage(err, "The PBX sync failed"));
    } finally {
      setSyncing(false);
    }
  };

  const handleImport = async (item: Integration) => {
    setImporting(item.key);
    try {
      const result = await integrationsApi.sync(item.key as "talkwisely" | "meetings");
      toast.success(result.message);
      load();
    } catch (err) {
      toast.error(apiErrorMessage(err, "The import failed"));
    } finally {
      setImporting(null);
    }
  };

  const handleTest = async (item: Integration) => {
    setTesting(item.key);
    try {
      const result = await integrationsApi.test(item.key);
      const timing = result.latency_ms !== null ? ` (${result.latency_ms} ms)` : "";
      if (result.ok) toast.success(`${result.message}${timing}`);
      else toast.error(result.message);
    } catch (err) {
      toast.error(apiErrorMessage(err, "The connection test failed"));
    } finally {
      setTesting(null);
    }
  };

  const openEditor = (item: Integration) => {
    setEditing(item);
    setDraft({ is_enabled: item.is_enabled, provider: item.provider, config: { ...item.config } });
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editing || !draft) return;
    setSaving(true);
    try {
      const updated = await integrationsApi.update(editing.key, draft);
      setIntegrations((all) => all.map((i) => (i.key === updated.key ? updated : i)));
      toast.success(`${updated.name} settings saved`);
      setEditing(null);
    } catch (err) {
      toast.error(apiErrorMessage(err, "Couldn't save these settings"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell title="Integrations & Adapters" subtitle="Manage TalkWisely Cloud PBX, CRM, Calendar, and Email provider connections">
      <div className="space-y-6">
        {/* TalkWisely PBX Spotlight Banner */}
        <Card className="bg-muted/50">
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center gap-2">
              <Phone className="size-5" />
              TalkWisely Cloud PBX Integration
              <Badge variant="secondary">Primary VoIP Adapter</Badge>
            </CardTitle>
            <CardDescription className="text-xs">
              Ingest VoIP call recordings and call metadata into TalkWiseAI. The current adapter is a mock that returns
              sample calls, because the TalkWisely API isn&apos;t available to this project; imported calls are analyzed like uploads.
            </CardDescription>
            {canOperate && (
              <CardAction>
                <Button size="sm" onClick={handleSync} disabled={syncing || !pbx?.is_enabled}>
                  <RefreshCw data-icon="inline-start" className={syncing ? "animate-spin" : ""} />
                  {syncing ? "Syncing PBX..." : "Sync TalkWisely Calls"}
                </Button>
              </CardAction>
            )}
          </CardHeader>
        </Card>

        {loading && integrations.length === 0 ? (
          <PageLoading />
        ) : error ? (
          <ErrorState message={error} onRetry={() => { setLoading(true); setError(""); load(); }} />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {integrations.map((item) => {
              const IconComp = icons[item.key] || Zap;
              return (
                <Card key={item.key}>
                  <CardHeader>
                    <div className="flex items-center gap-3">
                      <div className="size-9 rounded-lg border bg-muted flex items-center justify-center">
                        <IconComp className="size-5" />
                      </div>
                      <div>
                        <CardTitle className="text-sm">{item.name}</CardTitle>
                        <CardDescription className="text-[10px] font-medium">{item.provider_label}</CardDescription>
                      </div>
                    </div>
                    <CardAction>
                      {item.is_enabled ? (
                        <Badge variant="outline">
                          <FlaskConical data-icon="inline-start" />
                          {item.is_mock ? "Mock adapter" : "Enabled"}
                        </Badge>
                      ) : (
                        <Badge variant="secondary">
                          <CircleSlash data-icon="inline-start" />
                          Turned off
                        </Badge>
                      )}
                    </CardAction>
                  </CardHeader>
                  <CardContent className="flex-1 space-y-2">
                    <p className="text-xs text-muted-foreground leading-relaxed">{item.description}</p>
                    {item.config_fields.length > 0 && (
                      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
                        {item.config_fields.map((f) => (
                          <div key={f.key} className="contents">
                            <dt className="text-muted-foreground">{f.label}</dt>
                            <dd className="font-medium">{String(item.config[f.key] ?? "-")}</dd>
                          </div>
                        ))}
                      </dl>
                    )}
                  </CardContent>
                  <CardFooter className="border-t justify-between gap-2 text-xs text-muted-foreground">
                    <span>Last sync: {item.last_synced_at ? formatDateTime(item.last_synced_at) : "never"}</span>
                    <div className="flex items-center gap-1">
                      {canOperate && item.key === "meetings" && (
                        <Button variant="ghost" size="xs" onClick={() => handleImport(item)} disabled={importing === item.key || !item.is_enabled}>
                          {importing === item.key ? <Spinner data-icon="inline-start" /> : <RefreshCw data-icon="inline-start" />}
                          Sync now
                        </Button>
                      )}
                      {canOperate && (
                        <Button variant="ghost" size="xs" onClick={() => handleTest(item)} disabled={testing === item.key}>
                          {testing === item.key && <Spinner data-icon="inline-start" />}
                          Test connection
                        </Button>
                      )}
                      {isAdmin && (
                        <Button variant="outline" size="xs" onClick={() => openEditor(item)}>
                          <Settings2 data-icon="inline-start" />
                          Configure
                        </Button>
                      )}
                    </div>
                  </CardFooter>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      <Dialog open={editing !== null} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent>
          {editing && draft && (
            <form onSubmit={handleSave} className="contents">
              <DialogHeader>
                <DialogTitle>Configure {editing.name}</DialogTitle>
                <DialogDescription>
                  API keys and OAuth secrets are set in the backend environment, never here.
                </DialogDescription>
              </DialogHeader>
              <FieldGroup className="gap-4">
                <FieldLabel htmlFor="integration-enabled">
                  <Field orientation="horizontal">
                    <FieldContent>
                      <span className="text-sm font-medium">Enabled</span>
                      <FieldDescription className="text-xs">When off, this adapter won&apos;t be used.</FieldDescription>
                    </FieldContent>
                    <Switch
                      id="integration-enabled"
                      checked={draft.is_enabled}
                      onCheckedChange={(v) => setDraft({ ...draft, is_enabled: v })}
                    />
                  </Field>
                </FieldLabel>
                <Field>
                  <FieldLabel htmlFor="integration-provider">Provider</FieldLabel>
                  <Select value={draft.provider} onValueChange={(v) => setDraft({ ...draft, provider: v })}>
                    <SelectTrigger id="integration-provider"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {editing.providers.map((p) => (
                        <SelectItem key={p.key} value={p.key} disabled={!p.available}>
                          {p.label}{p.available ? "" : ` (${p.note.toLowerCase()})`}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                {editing.config_fields.map((f) => (
                  <Field key={f.key}>
                    <FieldLabel htmlFor={`cfg-${f.key}`}>{f.label}</FieldLabel>
                    <Input
                      id={`cfg-${f.key}`}
                      type={f.type}
                      min={f.min ?? undefined}
                      max={f.max ?? undefined}
                      value={String(draft.config[f.key] ?? "")}
                      onChange={(e) => setDraft({
                        ...draft,
                        config: { ...draft.config, [f.key]: f.type === "number" ? Number(e.target.value) : e.target.value },
                      })}
                    />
                    {f.description && <FieldDescription className="text-xs">{f.description}</FieldDescription>}
                  </Field>
                ))}
              </FieldGroup>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setEditing(null)}>Cancel</Button>
                <Button type="submit" disabled={saving}>
                  {saving && <Spinner data-icon="inline-start" />}
                  Save
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
