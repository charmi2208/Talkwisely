"use client";

import { AppShell } from "@/components/layout/AppShell";
import { Construction } from "lucide-react";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";

export default function Page() {
  return (
    <AppShell title="Meetings" subtitle="Recorded video and audio meeting sessions">
      <Empty className="border bg-card p-16">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <Construction />
          </EmptyMedia>
          <EmptyTitle>Meetings Workspace</EmptyTitle>
          <EmptyDescription>Video and audio meeting integration with auto-transcription and meeting minutes generator.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    </AppShell>
  );
}
