"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
import {
  Brain,
  LayoutDashboard,
  MessageSquare,
  TrendingUp,
  Users,
  CheckSquare,
  BarChart3,
  FileText,
  BookOpen,
  Bot,
  Settings,
  LogOut,
  Bell,
  ChevronLeft,
  ChevronRight,
  Plug,
  UserCircle,
  PhoneCall,
} from "lucide-react";
import { useAuthStore } from "@/lib/stores/authStore";
import toast from "react-hot-toast";
import { clsx } from "clsx";

const navItems = [
  {
    section: "Overview",
    items: [
      { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
    ],
  },
  {
    section: "Intelligence",
    items: [
      { href: "/conversations", icon: PhoneCall, label: "Conversations" },
      { href: "/meetings", icon: MessageSquare, label: "Meetings" },
      { href: "/sales", icon: TrendingUp, label: "Sales Intelligence" },
      { href: "/leads", icon: Users, label: "Leads" },
    ],
  },
  {
    section: "Actions",
    items: [
      { href: "/action-items", icon: CheckSquare, label: "Action Items" },
      { href: "/ai-assistant", icon: Bot, label: "AI Copilot" },
      { href: "/knowledge-base", icon: BookOpen, label: "Knowledge Base" },
    ],
  },
  {
    section: "Reports",
    items: [
      { href: "/analytics", icon: BarChart3, label: "Analytics" },
      { href: "/reports", icon: FileText, label: "Reports" },
      { href: "/team", icon: Users, label: "Team" },
    ],
  },
  {
    section: "Settings",
    items: [
      { href: "/integrations", icon: Plug, label: "Integrations" },
      { href: "/settings", icon: Settings, label: "Settings" },
      { href: "/profile", icon: UserCircle, label: "Profile" },
    ],
  },
];

interface AppSidebarProps {
  collapsed: boolean;
  setCollapsed: (v: boolean) => void;
}

export function AppSidebar({ collapsed, setCollapsed }: AppSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, clearAuth } = useAuthStore();

  const handleLogout = () => {
    clearAuth();
    toast.success("Signed out successfully");
    router.push("/login");
  };

  const isActive = (href: string) => {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  };

  return (
    <aside
      className={clsx(
        "flex flex-col h-full bg-white border-r border-slate-200 transition-all duration-300 shadow-sm z-20",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* Logo */}
      <div className={clsx("flex items-center h-16 px-4 border-b border-slate-100", collapsed ? "justify-center" : "gap-3")}>
        <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0 shadow-sm">
          <Brain className="w-5 h-5 text-white" />
        </div>
        {!collapsed && (
          <span className="text-base font-bold text-slate-900 truncate tracking-tight">TalkWiseAI</span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-2">
        {navItems.map((section) => (
          <div key={section.section} className="mb-5">
            {!collapsed && (
              <div className="px-3 mb-2">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  {section.section}
                </span>
              </div>
            )}
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const active = isActive(item.href);
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={clsx(
                        "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 group",
                        active
                          ? "bg-indigo-50 text-indigo-600 font-semibold"
                          : "text-slate-600 hover:text-slate-900 hover:bg-slate-50",
                        collapsed && "justify-center"
                      )}
                      title={collapsed ? item.label : undefined}
                    >
                      <item.icon
                        className={clsx("w-4 h-4 flex-shrink-0", active ? "text-indigo-600" : "text-slate-400 group-hover:text-slate-600")}
                      />
                      {!collapsed && <span>{item.label}</span>}
                      {active && !collapsed && (
                        <span className="ml-auto w-1.5 h-1.5 rounded-full bg-indigo-600" />
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* User / logout */}
      <div className="border-t border-slate-100 p-3 bg-slate-50/50">
        {!collapsed && user && (
          <div className="flex items-center gap-3 px-2 py-2 mb-1">
            <div className="w-8 h-8 rounded-full bg-indigo-100 border border-indigo-200 flex items-center justify-center flex-shrink-0 text-indigo-700 text-xs font-bold">
              {user.full_name.charAt(0)}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-900 truncate">{user.full_name}</p>
              <p className="text-xs text-slate-500 truncate">{user.email}</p>
            </div>
          </div>
        )}
        <button
          onClick={handleLogout}
          className={clsx(
            "flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm font-medium text-slate-600 hover:text-red-600 hover:bg-red-50 transition-all",
            collapsed && "justify-center"
          )}
          title={collapsed ? "Sign out" : undefined}
        >
          <LogOut className="w-4 h-4 flex-shrink-0" />
          {!collapsed && <span>Sign out</span>}
        </button>
      </div>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-20 w-6 h-6 rounded-full bg-white border border-slate-200 shadow-sm flex items-center justify-center text-slate-500 hover:text-slate-900 hover:bg-slate-50 transition-all z-30"
      >
        {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
      </button>
    </aside>
  );
}

interface AppHeaderProps {
  title: string;
  subtitle?: string;
}

export function AppHeader({ title, subtitle }: AppHeaderProps) {
  const { user } = useAuthStore();

  return (
    <header className="h-16 flex items-center justify-between px-6 border-b border-slate-200 bg-white/90 backdrop-blur-sm z-10">
      <div>
        <h1 className="text-lg font-bold text-slate-900 tracking-tight">{title}</h1>
        {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-3">
        <button className="relative w-9 h-9 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-all">
          <Bell className="w-4 h-4" />
          <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-indigo-600" />
        </button>
        <div className="w-9 h-9 rounded-lg bg-indigo-600 flex items-center justify-center text-white text-sm font-semibold shadow-sm">
          {user?.full_name?.charAt(0) || "U"}
        </div>
      </div>
    </header>
  );
}

interface AppShellProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}

export function AppShell({ title, subtitle, children }: AppShellProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 font-sans">
      <div className="relative flex-shrink-0">
        <AppSidebar collapsed={collapsed} setCollapsed={setCollapsed} />
      </div>
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <AppHeader title={title} subtitle={subtitle} />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
