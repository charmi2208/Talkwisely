"use client";

import { useState } from "react";
import { toast } from "sonner";
import { AppShell } from "@/components/layout/AppShell";
import { authApi } from "@/lib/api/auth";
import { apiErrorMessage } from "@/lib/api/errors";
import { usersApi } from "@/lib/api/users";
import { useAuthStore, useRole } from "@/lib/stores/authStore";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";

export default function Page() {
  const { user, setUser } = useAuthStore();
  const role = useRole();
  const [editedName, setEditedName] = useState<string | null>(null);
  const fullName = editedName ?? user?.full_name ?? "";
  const setFullName = setEditedName;
  const [savingName, setSavingName] = useState(false);
  const [passwords, setPasswords] = useState({ current: "", next: "", confirm: "" });
  const [savingPassword, setSavingPassword] = useState(false);

  const saveName = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName.trim()) return;
    setSavingName(true);
    try {
      await usersApi.updateMe(fullName.trim());
      setUser(await authApi.me());
      setEditedName(null);
      toast.success("Name updated");
    } catch (err) {
      toast.error(apiErrorMessage(err, "Couldn't update your name"));
    } finally {
      setSavingName(false);
    }
  };

  const savePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passwords.next !== passwords.confirm) {
      toast.error("The new passwords don't match");
      return;
    }
    setSavingPassword(true);
    try {
      await usersApi.changePassword(passwords.current, passwords.next);
      setPasswords({ current: "", next: "", confirm: "" });
      toast.success("Password changed");
    } catch (err) {
      toast.error(apiErrorMessage(err, "Couldn't change your password"));
    } finally {
      setSavingPassword(false);
    }
  };

  return (
    <AppShell title="Profile" subtitle="Manage your account profile and credentials">
      <div className="max-w-2xl space-y-6">
        <Card>
          <CardHeader className="border-b">
            <div className="flex items-center gap-4">
              <Avatar className="size-16">
                <AvatarFallback className="text-2xl font-semibold">
                  {user?.full_name?.charAt(0) || "U"}
                </AvatarFallback>
              </Avatar>
              <div className="flex flex-col gap-1">
                <CardTitle className="text-lg">{user?.full_name || "User Account"}</CardTitle>
                <CardDescription>{user?.email}{user?.organization_name ? ` · ${user.organization_name}` : ""}</CardDescription>
                <Badge variant="secondary" className="capitalize">
                  Role: {role}
                </Badge>
              </div>
            </div>
          </CardHeader>

          <form onSubmit={saveName}>
            <CardContent>
              <FieldGroup className="gap-4">
                <Field className="gap-1.5">
                  <FieldLabel htmlFor="profile-name" className="text-xs">Full Name</FieldLabel>
                  <Input id="profile-name" type="text" required value={fullName} onChange={(e) => setFullName(e.target.value)} />
                </Field>
                <Field className="gap-1.5">
                  <FieldLabel htmlFor="profile-email" className="text-xs">Email Address</FieldLabel>
                  <Input id="profile-email" type="email" readOnly value={user?.email || ""} className="bg-muted" />
                  <FieldDescription className="text-xs">Ask an admin if your email needs to change.</FieldDescription>
                </Field>
              </FieldGroup>
            </CardContent>
            <CardFooter className="justify-end pt-4">
              <Button type="submit" size="sm" disabled={savingName || fullName.trim() === user?.full_name}>
                {savingName && <Spinner data-icon="inline-start" />}
                Save name
              </Button>
            </CardFooter>
          </form>
        </Card>

        <Card>
          <CardHeader className="border-b">
            <CardTitle>Change password</CardTitle>
            <CardDescription>Use at least 8 characters.</CardDescription>
          </CardHeader>
          <form onSubmit={savePassword}>
            <CardContent>
              <FieldGroup className="gap-4">
                <Field className="gap-1.5">
                  <FieldLabel htmlFor="current-password" className="text-xs">Current password</FieldLabel>
                  <Input id="current-password" type="password" autoComplete="current-password" required
                    value={passwords.current} onChange={(e) => setPasswords({ ...passwords, current: e.target.value })} />
                </Field>
                <Field className="gap-1.5">
                  <FieldLabel htmlFor="new-password" className="text-xs">New password</FieldLabel>
                  <Input id="new-password" type="password" autoComplete="new-password" minLength={8} required
                    value={passwords.next} onChange={(e) => setPasswords({ ...passwords, next: e.target.value })} />
                </Field>
                <Field className="gap-1.5">
                  <FieldLabel htmlFor="confirm-password" className="text-xs">Confirm new password</FieldLabel>
                  <Input id="confirm-password" type="password" autoComplete="new-password" minLength={8} required
                    value={passwords.confirm} onChange={(e) => setPasswords({ ...passwords, confirm: e.target.value })} />
                </Field>
              </FieldGroup>
            </CardContent>
            <CardFooter className="justify-end pt-4">
              <Button type="submit" size="sm" disabled={savingPassword}>
                {savingPassword && <Spinner data-icon="inline-start" />}
                Change password
              </Button>
            </CardFooter>
          </form>
        </Card>
      </div>
    </AppShell>
  );
}
