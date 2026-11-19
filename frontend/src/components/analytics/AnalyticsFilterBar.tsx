"use client";

import { useEffect, useState } from "react";
import { Filter } from "lucide-react";
import type { AnalyticsFilters } from "@/lib/api/analytics";
import { usersApi, type TeamMember } from "@/lib/api/users";
import { useRole } from "@/lib/stores/authStore";
import { CONVERSATION_TYPES, humanize } from "@/lib/format";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const PERIODS = [
  { value: "7", label: "Last 7 days" },
  { value: "30", label: "Last 30 days" },
  { value: "90", label: "Last 90 days" },
  { value: "365", label: "Last 12 months" },
];

/** Date range, conversation type and (for admins/managers) team member filters. */
export function AnalyticsFilterBar({
  value,
  onChange,
}: {
  value: AnalyticsFilters;
  onChange: (next: AnalyticsFilters) => void;
}) {
  const role = useRole();
  const canFilterPeople = role !== "agent";
  const [members, setMembers] = useState<TeamMember[]>([]);

  useEffect(() => {
    if (!canFilterPeople) return;
    usersApi.list().then(setMembers).catch(() => setMembers([]));
  }, [canFilterPeople]);

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Filter className="size-4 text-muted-foreground" aria-hidden />
      <Select value={String(value.days ?? 30)} onValueChange={(v) => onChange({ ...value, days: Number(v) })}>
        <SelectTrigger size="sm" aria-label="Date range">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {PERIODS.map((p) => (
            <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select
        value={value.conversation_type ?? "all"}
        onValueChange={(v) => onChange({ ...value, conversation_type: v === "all" ? undefined : v })}
      >
        <SelectTrigger size="sm" aria-label="Conversation type">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All conversation types</SelectItem>
          {CONVERSATION_TYPES.map((t) => (
            <SelectItem key={t} value={t}>{humanize(t)}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      {canFilterPeople && (
        <Select
          value={value.agent_id ?? "all"}
          onValueChange={(v) => onChange({ ...value, agent_id: v === "all" ? undefined : v })}
        >
          <SelectTrigger size="sm" aria-label="Team member">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Whole team</SelectItem>
            {members.map((m) => (
              <SelectItem key={m.id} value={m.id}>{m.full_name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
    </div>
  );
}
