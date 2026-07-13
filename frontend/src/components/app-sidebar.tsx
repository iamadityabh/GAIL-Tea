import { Link, useRouterState } from "@tanstack/react-router";
import {
  User,
  BarChart3,
  Calendar,
  UserPlus,
  Building2,
  CalendarPlus,
  Wand2,
} from "lucide-react";

import gailEmblem from "@/assets/gail-emblem.jpg";

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

const groups = [
  {
    label: "Ask a Query",
    items: [
      { title: "Single Employee", url: "/portal/query/single", icon: User },
      { title: "Team & Overall", url: "/portal/query/overall", icon: BarChart3 },
      { title: "Events", url: "/portal/query/events", icon: Calendar },
    ],
  },
  {
    label: "Add Data",
    items: [
      { title: "Employees", url: "/portal/add/employees", icon: UserPlus },
      { title: "Departments", url: "/portal/add/departments", icon: Building2 },
      { title: "Events", url: "/portal/add/events", icon: CalendarPlus },
    ],
  },
  {
    label: "Update Data",
    items: [{ title: "AI Update Agent", url: "/portal/update", icon: Wand2 }],
  },
] as const;

export function AppSidebar() {
  const pathname = useRouterState({ select: (r) => r.location.pathname });
  const isActive = (u: string) => pathname === u;

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b border-sidebar-border px-4 py-5">
        <Link to="/" className="flex items-center gap-3">
          <span className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-molten/10 p-1 ring-1 ring-molten/30 shadow-[var(--shadow-glow)]">
            <img
              src={gailEmblem}
              alt="GAIL logo"
              className="h-full w-full object-contain"
            />
          </span>
          <div className="flex min-w-0 flex-col leading-none group-data-[collapsible=icon]:hidden">
            <span className="font-display text-base font-semibold tracking-tight">
              GTI PORTAL
            </span>
            <span className="mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground">
              GAIL Training Inst.
            </span>
          </div>
        </Link>
      </SidebarHeader>
      <SidebarContent>
        {groups.map((g) => (
          <SidebarGroup key={g.label}>
            <SidebarGroupLabel className="mono text-[10px] uppercase tracking-[0.2em]">
              {g.label}
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {g.items.map((item) => (
                  <SidebarMenuItem key={item.url}>
                    <SidebarMenuButton
                      asChild
                      isActive={isActive(item.url)}
                      tooltip={item.title}
                    >
                      <Link to={item.url} className="flex items-center gap-2">
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>
    </Sidebar>
  );
}
