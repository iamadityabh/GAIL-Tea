import { createFileRoute, Outlet, Link } from "@tanstack/react-router";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";

import gailEmblem from "@/assets/gail-emblem.jpg";

export const Route = createFileRoute("/portal")({
  component: PortalLayout,
});

function PortalLayout() {
  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-background text-foreground">
        <AppSidebar />
        <div className="flex flex-1 flex-col">
          <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-hairline bg-background/70 px-4 backdrop-blur">
            <SidebarTrigger className="text-foreground hover:text-molten" />
            <div className="h-4 w-px bg-hairline" />
            <Link to="/" className="mono flex min-w-0 items-center gap-2 text-[11px] uppercase tracking-[0.25em] text-muted-foreground hover:text-foreground">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-molten/10 p-1 ring-1 ring-molten/30">
                <img
                  src={gailEmblem}
                  alt="GAIL logo"
                  className="h-full w-full object-contain"
                />
              </span>
              <span className="hidden sm:inline">GTI · HR Portal</span>
            </Link>
            <div className="ml-auto flex items-center gap-2">
              <span className="mono hidden rounded-full border border-hairline px-2 py-0.5 text-[10px] uppercase tracking-[0.25em] text-molten md:inline">
                ● live
              </span>
            </div>
          </header>
          <main className="flex-1 overflow-hidden">
            <Outlet />
          </main>
        </div>
      </div>
    </SidebarProvider>
  );
}
