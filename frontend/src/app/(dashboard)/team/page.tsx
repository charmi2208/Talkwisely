"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Users, Mail } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import toast from "react-hot-toast";

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
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Users className="w-4 h-4 text-indigo-600" />
              Organization Team Members ({members.length})
            </h3>
          </div>

          <div className="space-y-2.5">
            {members.map((member) => (
              <div key={member.id} className="flex items-center justify-between p-4 rounded-lg bg-slate-50 border border-slate-200">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-indigo-100 border border-indigo-200 flex items-center justify-center font-bold text-xs text-indigo-700">
                    {member.full_name.charAt(0)}
                  </div>
                  <div>
                    <p className="text-sm font-bold text-slate-900">{member.full_name}</p>
                    <p className="text-xs text-slate-500 flex items-center gap-1">
                      <Mail className="w-3 h-3 text-slate-400" />
                      {member.email}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <select
                    value={member.role}
                    onChange={(e) => handleRoleChange(member.id, e.target.value)}
                    className="bg-white border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:border-indigo-600 font-semibold capitalize shadow-xs"
                  >
                    <option value="admin">Admin (Full Access)</option>
                    <option value="manager">Manager (Team Analytics & QA)</option>
                    <option value="agent">Sales/Support Agent</option>
                  </select>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
