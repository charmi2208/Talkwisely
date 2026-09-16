"use client";

import { AppShell } from "@/components/layout/AppShell";
import { Users } from "lucide-react";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";

export default function Page() {
  return (
    <AppShell title="Leads" subtitle="High-intent sales prospects and lead scoring dashboard">
      <Empty className="border bg-card p-16">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <Users />
          </EmptyMedia>
          <EmptyTitle>Leads Directory</EmptyTitle>
          <EmptyDescription>Manage conversation-qualified prospects and automated CRM lead syncing.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    </AppShell>
  );
}
