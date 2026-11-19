"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { CalendarClock, Copy, Download, ExternalLink, MessageSquare, RefreshCw, Search } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { apiErrorMessage } from "@/lib/api/errors";
import { integrationsApi } from "@/lib/api/integrations";
import { meetingsApi, type MeetingItem, type MeetingMinutes } from "@/lib/api/meetings";
import { useRole } from "@/lib/stores/authStore";
import { saveBlob } from "@/lib/download";
import { formatDate, formatDuration, humanize } from "@/lib/format";
import { ErrorState, PageLoading } from "@/components/common/ErrorState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { InputGroup, InputGroupAddon, InputGroupInput } from "@/components/ui/input-group";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Spinner } from "@/components/ui/spinner";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

function MinutesSection({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="space-y-1.5">
      <h3 className="text-sm font-semibold">{title}</h3>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">Not found in the available conversation.</p>
      ) : (
        <ul className="list-disc space-y-1 pl-5 text-sm">
          {items.map((item, i) => <li key={i}>{item}</li>)}
        </ul>
      )}
    </div>
  );
}

export default function MeetingsPage() {
  const [meetings, setMeetings] = useState<MeetingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [scope, setScope] = useState<"meetings" | "all">("all");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<MeetingItem | null>(null);
  const [minutes, setMinutes] = useState<MeetingMinutes | null>(null);
  const [minutesLoading, setMinutesLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const canImport = useRole() !== "agent";

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setMeetings(await meetingsApi.list({ meetings_only: scope === "meetings", search: search.trim() || undefined }));
    } catch (err) {
      setError(apiErrorMessage(err, "Meetings couldn't be loaded."));
    } finally {
      setLoading(false);
    }
  }, [scope, search]);

  useEffect(() => {
    const timer = setTimeout(load, search ? 300 : 0);
    return () => clearTimeout(timer);
  }, [load, search]);

  const importRecordings = async () => {
    setImporting(true);
    try {
      const result = await integrationsApi.sync("meetings");
      toast.success(`${result.message} Minutes appear here once analysis finishes.`);
    } catch (err) {
      toast.error(apiErrorMessage(err, "Couldn't import meeting recordings"));
    } finally {
      setImporting(false);
    }
  };

  const openMinutes = async (meeting: MeetingItem) => {
    setSelected(meeting);
    setMinutes(null);
    setMinutesLoading(true);
    try {
      setMinutes(await meetingsApi.minutes(meeting.conversation_id));
    } catch (err) {
      toast.error(apiErrorMessage(err, "Couldn't load the minutes"));
      setSelected(null);
    } finally {
      setMinutesLoading(false);
    }
  };

  const slug = (title: string) => title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "meeting";

  return (
    <AppShell title="Meetings" subtitle="Recorded video and audio meeting sessions">
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <ToggleGroup type="single" variant="outline" size="sm" value={scope} onValueChange={(v) => v && setScope(v as "meetings" | "all")}>
            <ToggleGroupItem value="all">All conversations with minutes</ToggleGroupItem>
            <ToggleGroupItem value="meetings">Meetings only</ToggleGroupItem>
          </ToggleGroup>
          <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
            <InputGroup className="w-full sm:w-64">
              <InputGroupAddon><Search /></InputGroupAddon>
              <InputGroupInput placeholder="Search meetings" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search meetings" />
            </InputGroup>
            {canImport && (
              <Button variant="outline" size="sm" onClick={importRecordings} disabled={importing}>
                {importing ? <Spinner data-icon="inline-start" /> : <RefreshCw data-icon="inline-start" />}
                Import recordings
              </Button>
            )}
          </div>
        </div>

        {loading && meetings.length === 0 ? (
          <PageLoading />
        ) : error ? (
          <ErrorState message={error} onRetry={load} />
        ) : meetings.length === 0 ? (
          <Empty className="border bg-card p-16">
            <EmptyHeader>
              <EmptyMedia variant="icon"><MessageSquare /></EmptyMedia>
              <EmptyTitle>No meeting minutes yet</EmptyTitle>
              <EmptyDescription>
                Upload a meeting recording under Conversations; minutes are generated automatically once it&apos;s analyzed.
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {meetings.map((m) => (
              <Card key={m.conversation_id} className="cursor-pointer transition-colors hover:bg-muted/40" onClick={() => openMinutes(m)}>
                <CardHeader>
                  <CardTitle className="line-clamp-2">{m.title}</CardTitle>
                  <CardDescription className="text-xs">
                    {formatDate(m.occurred_at ?? m.created_at)} · {formatDuration(m.duration_seconds)}
                  </CardDescription>
                  <CardAction>
                    <Badge variant="outline">{humanize(m.conversation_type)}</Badge>
                  </CardAction>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground line-clamp-3">
                    {m.objective ?? "Objective not found in the available conversation."}
                  </p>
                </CardContent>
                <CardFooter className="gap-4 border-t text-xs text-muted-foreground tabular-nums">
                  <span>{m.decisions_count} decisions</span>
                  <span>{m.action_items_count} action items</span>
                  <span>{m.open_questions_count} open questions</span>
                </CardFooter>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Sheet open={selected !== null} onOpenChange={(open) => !open && setSelected(null)}>
        <SheetContent className="w-full sm:max-w-xl">
          <SheetHeader>
            <SheetTitle>{selected?.title}</SheetTitle>
            <SheetDescription>AI-generated meeting minutes. Check them against the transcript before sharing.</SheetDescription>
          </SheetHeader>
          {minutesLoading || !minutes ? (
            <div className="flex flex-1 items-center justify-center"><Spinner className="size-6" /></div>
          ) : (
            <>
              <div className="flex flex-wrap gap-2 px-4">
                <Button size="sm" variant="outline" onClick={() => saveBlob(minutes.formatted_markdown, `${slug(minutes.title)}-minutes.md`, "text/markdown")}>
                  <Download data-icon="inline-start" /> Download .md
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => navigator.clipboard.writeText(minutes.formatted_markdown).then(() => toast.success("Minutes copied"))}
                >
                  <Copy data-icon="inline-start" /> Copy
                </Button>
                <Button size="sm" variant="ghost" asChild>
                  <Link href={`/conversations/${minutes.conversation_id}`}>
                    <ExternalLink data-icon="inline-start" /> Open conversation
                  </Link>
                </Button>
              </div>
              <ScrollArea className="min-h-0 flex-1 px-4 pb-4">
                <div className="space-y-5">
                  <div className="space-y-1.5">
                    <h3 className="text-sm font-semibold">Objective</h3>
                    <p className="text-sm">{minutes.objective ?? "Not found in the available conversation."}</p>
                  </div>
                  <div className="space-y-1.5">
                    <h3 className="text-sm font-semibold">Participants</h3>
                    <p className="text-sm">{minutes.participants_summary ?? "Not found in the available conversation."}</p>
                  </div>
                  <Separator />
                  <MinutesSection title="Discussion points" items={minutes.discussion_points} />
                  <MinutesSection title="Decisions" items={minutes.decisions} />
                  <MinutesSection title="Action items" items={minutes.action_items_summary} />
                  <MinutesSection title="Open questions" items={minutes.open_questions} />
                  <MinutesSection title="Risks" items={minutes.risks} />
                  <MinutesSection title="Next steps" items={minutes.next_steps} />
                  {minutes.next_meeting && (
                    <div className="flex items-center gap-2 text-sm">
                      <CalendarClock className="size-4 text-muted-foreground" />
                      Next meeting: {minutes.next_meeting}
                    </div>
                  )}
                </div>
              </ScrollArea>
            </>
          )}
        </SheetContent>
      </Sheet>
    </AppShell>
  );
}
