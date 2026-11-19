"use client";

import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Users, Mail, UserPlus } from "lucide-react";
import { toast } from "sonner";
import { apiErrorMessage } from "@/lib/api/errors";
import { usersApi, type TeamMember } from "@/lib/api/users";
import { useAuthStore, useRole } from "@/lib/stores/authStore";
import { formatDate } from "@/lib/format";
import { ErrorState, PageLoading } from "@/components/common/ErrorState";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Item, ItemActions, ItemContent, ItemDescription, ItemGroup, ItemMedia, ItemTitle,
} from "@/components/ui/item";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";

const ROLE_LABELS: Record<string, string> = {
  admin: "Admin (Full Access)",
  manager: "Manager (Team Analytics & QA)",
  agent: "Sales/Support Agent",
};

const EMPTY_FORM = { full_name: "", email: "", role: "agent", temporary_password: "" };

export default function TeamPage() {
  const role = useRole();
  const isAdmin = role === "admin";
  const currentUserId = useAuthStore((s) => s.user?.id);
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [confirming, setConfirming] = useState<TeamMember | null>(null);

  const loadMembers = useCallback(async () => {
    try {
      const list = await usersApi.list();
      setMembers(list);
      setError("");
    } catch (err) {
      setError(apiErrorMessage(err, "Team members couldn't be loaded."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMembers();
  }, [loadMembers]);

  const replace = (updated: TeamMember) =>
    setMembers((all) => all.map((m) => (m.id === updated.id ? { ...m, ...updated, conversation_count: m.conversation_count } : m)));

  const handleRoleChange = async (member: TeamMember, newRole: string) => {
    try {
      replace(await usersApi.setRole(member.id, newRole));
      toast.success(`${member.full_name} is now ${newRole === "agent" ? "an agent" : `a ${newRole}`}`);
    } catch (err) {
      toast.error(apiErrorMessage(err, "Couldn't update the role"));
    }
  };

  const toggleActive = async (member: TeamMember) => {
    try {
      replace(await usersApi.update(member.id, { is_active: !member.is_active }));
      toast.success(member.is_active ? `${member.full_name} can no longer sign in` : `${member.full_name} can sign in again`);
    } catch (err) {
      toast.error(apiErrorMessage(err, "Couldn't update the account"));
    } finally {
      setConfirming(null);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const created = await usersApi.create(form);
      setMembers((all) => [created, ...all]);
      toast.success(`Added ${created.full_name}. Share the temporary password with them.`);
      setForm(EMPTY_FORM);
      setAdding(false);
    } catch (err) {
      toast.error(apiErrorMessage(err, "Couldn't add this member"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell title="Team & User Roles" subtitle="Manage organization team members and role-based permissions (Admin, Manager, Agent)">
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="size-4" />
              Organization Team Members ({members.length})
            </CardTitle>
            <CardDescription>
              {isAdmin
                ? "Admins manage members and roles. Agents see only their own conversations; managers see the whole team."
                : "Only admins can add members or change roles."}
            </CardDescription>
            {isAdmin && (
              <CardAction>
                <Button size="sm" onClick={() => setAdding(true)}>
                  <UserPlus data-icon="inline-start" />
                  Add member
                </Button>
              </CardAction>
            )}
          </CardHeader>

          <CardContent>
            {loading && members.length === 0 ? (
              <PageLoading />
            ) : error ? (
              <ErrorState message={error} onRetry={() => { setLoading(true); setError(""); loadMembers(); }} />
            ) : (
              <ItemGroup className="gap-2.5">
                {members.map((member) => {
                  const isSelf = member.id === currentUserId;
                  return (
                    <Item key={member.id} variant="muted" className={member.is_active ? "" : "opacity-60"}>
                      <ItemMedia>
                        <Avatar size="lg" className="size-9">
                          <AvatarFallback className="text-xs font-semibold">
                            {member.full_name.charAt(0)}
                          </AvatarFallback>
                        </Avatar>
                      </ItemMedia>
                      <ItemContent>
                        <ItemTitle>
                          {member.full_name}
                          {isSelf && <Badge variant="outline">You</Badge>}
                          {!member.is_active && <Badge variant="destructive">Deactivated</Badge>}
                        </ItemTitle>
                        <ItemDescription className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                          <span className="flex items-center gap-1"><Mail className="size-3" />{member.email}</span>
                          <span>{member.conversation_count ?? 0} conversations</span>
                          <span>Last sign-in {member.last_login_at ? formatDate(member.last_login_at) : "never"}</span>
                        </ItemDescription>
                      </ItemContent>

                      <ItemActions>
                        {isAdmin ? (
                          <>
                            <Select value={member.role} onValueChange={(v) => handleRoleChange(member, v)} disabled={isSelf}>
                              <SelectTrigger size="sm" className="bg-background text-xs font-medium" aria-label={`Role for ${member.full_name}`}>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {Object.entries(ROLE_LABELS).map(([value, label]) => (
                                  <SelectItem key={value} value={value}>{label}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            {!isSelf && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => (member.is_active ? setConfirming(member) : toggleActive(member))}
                              >
                                {member.is_active ? "Deactivate" : "Reactivate"}
                              </Button>
                            )}
                          </>
                        ) : (
                          <Badge variant="secondary">{ROLE_LABELS[member.role] ?? member.role}</Badge>
                        )}
                      </ItemActions>
                    </Item>
                  );
                })}
              </ItemGroup>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={adding} onOpenChange={setAdding}>
        <DialogContent>
          <form onSubmit={handleCreate} className="contents">
            <DialogHeader>
              <DialogTitle>Add a team member</DialogTitle>
              <DialogDescription>
                No email is sent. Share the temporary password with them; they can change it on their Profile page.
              </DialogDescription>
            </DialogHeader>
            <FieldGroup className="gap-4">
              <Field>
                <FieldLabel htmlFor="member-name">Full name</FieldLabel>
                <Input id="member-name" required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
              </Field>
              <Field>
                <FieldLabel htmlFor="member-email">Email</FieldLabel>
                <Input id="member-email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </Field>
              <Field>
                <FieldLabel htmlFor="member-role">Role</FieldLabel>
                <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                  <SelectTrigger id="member-role"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(ROLE_LABELS).map(([value, label]) => (
                      <SelectItem key={value} value={value}>{label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <Field>
                <FieldLabel htmlFor="member-password">Temporary password</FieldLabel>
                <Input
                  id="member-password"
                  type="text"
                  minLength={8}
                  required
                  value={form.temporary_password}
                  onChange={(e) => setForm({ ...form, temporary_password: e.target.value })}
                />
                <FieldDescription>At least 8 characters.</FieldDescription>
              </Field>
            </FieldGroup>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setAdding(false)}>Cancel</Button>
              <Button type="submit" disabled={saving}>
                {saving && <Spinner data-icon="inline-start" />}
                Add member
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={confirming !== null} onOpenChange={(open) => !open && setConfirming(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Deactivate {confirming?.full_name}?</AlertDialogTitle>
            <AlertDialogDescription>
              They won&apos;t be able to sign in. Their conversations and insights stay in the workspace, and you can reactivate them later.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={() => confirming && toggleActive(confirming)}>
              Deactivate
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  );
}
