"use client";

import { AppShell } from "@/components/layout/AppShell";
import { useAuthStore } from "@/lib/stores/authStore";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

export default function Page() {
  const { user } = useAuthStore();

  return (
    <AppShell title="Profile" subtitle="Manage your account profile and credentials">
      <Card className="max-w-2xl">
        <CardHeader className="border-b">
          <div className="flex items-center gap-4">
            <Avatar className="size-16">
              <AvatarFallback className="text-2xl font-semibold">
                {user?.full_name?.charAt(0) || "U"}
              </AvatarFallback>
            </Avatar>
            <div className="flex flex-col gap-1">
              <CardTitle className="text-lg">{user?.full_name || "User Account"}</CardTitle>
              <CardDescription>{user?.email}</CardDescription>
              <Badge variant="secondary" className="capitalize">
                Role: {user?.roles?.[0] || "agent"}
              </Badge>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          <FieldGroup className="gap-4">
            <Field className="gap-1.5">
              <FieldLabel htmlFor="profile-name" className="text-xs">Full Name</FieldLabel>
              <Input id="profile-name" type="text" readOnly value={user?.full_name || ""} className="bg-muted" />
            </Field>
            <Field className="gap-1.5">
              <FieldLabel htmlFor="profile-email" className="text-xs">Email Address</FieldLabel>
              <Input id="profile-email" type="email" readOnly value={user?.email || ""} className="bg-muted" />
            </Field>
          </FieldGroup>
        </CardContent>
      </Card>
    </AppShell>
  );
}
