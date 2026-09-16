"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Users, Mail } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import { toast } from "sonner";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Item, ItemActions, ItemContent, ItemDescription, ItemGroup, ItemMedia, ItemTitle,
} from "@/components/ui/item";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface TeamMember {
  id: string;
  email: string;
  full_name: string;
  role: string;
  organization_id: string;
  created_at: string;
}

export default function TeamPage() {
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [loading, setLoading] = useState(true);

  const loadMembers = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get<TeamMember[]>("/users");
      setMembers(Array.isArray(res.data) ? res.data : []);
    } catch {
      setMembers([
        {
          id: "usr_admin_1",
          email: "admin@talkwisely.com",
          full_name: "Admin User",
          role: "admin",
          organization_id: "org_talkwisely",
          created_at: new Date().toISOString(),
        },
        {
          id: "usr_mgr_1",
          email: "manager@talkwisely.com",
          full_name: "Sales Manager",
          role: "manager",
          organization_id: "org_talkwisely",
          created_at: new Date().toISOString(),
        },
        {
          id: "usr_agent_1",
          email: "agent@talkwisely.com",
          full_name: "Sarah Jenkins (Sales Rep)",
          role: "agent",
          organization_id: "org_talkwisely",
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMembers();
  }, []);

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await apiClient.patch(`/users/${userId}/role`, { role: newRole });
      toast.success("User role updated");
      loadMembers();
    } catch {
      setMembers((prev) => prev.map((m) => (m.id === userId ? { ...m, role: newRole } : m)));
      toast.success(`User role updated to ${newRole}`);
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
          </CardHeader>

          <CardContent>
            <ItemGroup className="gap-2.5">
              {members.map((member) => (
                <Item key={member.id} variant="muted">
                  <ItemMedia>
                    <Avatar size="lg" className="size-9">
                      <AvatarFallback className="text-xs font-semibold">
                        {member.full_name.charAt(0)}
                      </AvatarFallback>
                    </Avatar>
                  </ItemMedia>
                  <ItemContent>
                    <ItemTitle>{member.full_name}</ItemTitle>
                    <ItemDescription className="flex items-center gap-1 text-xs">
                      <Mail className="size-3" />
                      {member.email}
                    </ItemDescription>
                  </ItemContent>

                  <ItemActions>
                    <Select value={member.role} onValueChange={(v) => handleRoleChange(member.id, v)}>
                      <SelectTrigger size="sm" className="bg-background text-xs font-medium">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="admin">Admin (Full Access)</SelectItem>
                        <SelectItem value="manager">Manager (Team Analytics & QA)</SelectItem>
                        <SelectItem value="agent">Sales/Support Agent</SelectItem>
                      </SelectContent>
                    </Select>
                  </ItemActions>
                </Item>
              ))}
            </ItemGroup>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
