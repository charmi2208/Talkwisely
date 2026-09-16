"use client";

import { AppShell } from "@/components/layout/AppShell";
import { Settings } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldContent, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Switch } from "@/components/ui/switch";

const preferences = [
  {
    id: "auto-action-items",
    title: "Automatic Action Item Extraction",
    description: "Automatically extract tasks from uploaded call recordings using LLM pipeline",
  },
  {
    id: "lead-intent-alerts",
    title: "Real-Time Lead Intent Alerts",
    description: "Receive notifications when a high-intent lead score (80+) is detected",
  },
  {
    id: "pbx-auto-sync",
    title: "TalkWisely Cloud PBX Auto-Sync",
    description: "Sync new incoming calls from PBX webhook endpoints every 15 minutes",
  },
];

export default function Page() {
  return (
    <AppShell title="Settings" subtitle="System preferences, notification thresholds & AI model configurations">
      <Card className="max-w-3xl">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2">
            <Settings className="size-5" />
            Application Preferences
          </CardTitle>
        </CardHeader>

        <CardContent>
          <FieldGroup className="gap-4">
            {preferences.map((pref) => (
              <FieldLabel key={pref.id} htmlFor={pref.id}>
                <Field orientation="horizontal">
                  <FieldContent>
                    <span className="text-sm font-medium">{pref.title}</span>
                    <FieldDescription className="text-xs">{pref.description}</FieldDescription>
                  </FieldContent>
                  <Switch id={pref.id} defaultChecked />
                </Field>
              </FieldLabel>
            ))}
          </FieldGroup>
        </CardContent>
      </Card>
    </AppShell>
  );
}
