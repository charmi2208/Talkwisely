"use client";

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
  Plug,
  UserCircle,
  PhoneCall,
} from "lucide-react";
import { useAuthStore } from "@/lib/stores/authStore";
import { toast } from "sonner";
import { ModeToggle } from "@/components/mode-toggle";
import { NotificationsMenu } from "@/components/layout/NotificationsMenu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
} from "@/components/ui/sidebar";

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

export function AppSidebar() {
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
    <Sidebar collapsible="icon" variant="inset">
      {/* Logo */}
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/dashboard">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
                  <Brain className="size-4" />
                </div>
                <span className="truncate font-semibold">TalkWiseAI</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      {/* Navigation */}
      <SidebarContent>
        {navItems.map((section) => (
          <SidebarGroup key={section.section}>
            <SidebarGroupLabel>{section.section}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {section.items.map((item) => (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton asChild isActive={isActive(item.href)} tooltip={item.label}>
                      <Link href={item.href}>
                        <item.icon />
                        <span>{item.label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      {/* User / logout */}
      <SidebarFooter>
        <SidebarMenu>
          {user && (
            <SidebarMenuItem>
              <SidebarMenuButton size="lg" className="pointer-events-none">
                <Avatar className="rounded-lg">
                  <AvatarFallback className="rounded-lg">{user.full_name.charAt(0)}</AvatarFallback>
                </Avatar>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-medium">{user.full_name}</span>
                  <span className="truncate text-xs text-muted-foreground">{user.email}</span>
                </div>
              </SidebarMenuButton>
            </SidebarMenuItem>
          )}
          <SidebarMenuItem>
            <SidebarMenuButton onClick={handleLogout} tooltip="Sign out">
              <LogOut />
              <span>Sign out</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}

interface AppHeaderProps {
  title: string;
  subtitle?: string;
}

export function AppHeader({ title, subtitle }: AppHeaderProps) {
  const { user } = useAuthStore();

  return (
    <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-2 rounded-t-xl border-b bg-background/90 px-4 backdrop-blur-sm lg:px-6">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="mx-2 data-[orientation=vertical]:h-4" />
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-base font-semibold">{title}</h1>
        {subtitle && <p className="truncate text-xs text-muted-foreground">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-3">
        <ModeToggle />
        <NotificationsMenu />
        <Avatar size="lg" className="rounded-lg after:rounded-lg">
          <AvatarFallback className="rounded-lg bg-primary text-primary-foreground">
            {user?.full_name?.charAt(0) || "U"}
          </AvatarFallback>
        </Avatar>
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
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="min-w-0">
        <AppHeader title={title} subtitle={subtitle} />
        <div className="flex-1 p-4 lg:p-6">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  );
}
