import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";

import appCss from "../styles.css?url";
import gailEmblem from "@/assets/gail-emblem.jpg";
import { reportLovableError } from "../lib/lovable-error-reporting";
import { Toaster } from "@/components/ui/sonner";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <span className="mono text-[11px] uppercase tracking-[0.3em] text-molten">
          ERR / 404
        </span>
        <h1 className="mt-3 font-display text-7xl font-semibold">Off-grid</h1>
        <p className="mt-3 text-sm text-muted-foreground">
          The page you're looking for isn't in the GTI network.
        </p>
        <Link
          to="/"
          className="mt-6 inline-flex items-center rounded-md bg-molten px-4 py-2 text-sm font-medium text-primary-foreground shadow-[var(--shadow-glow)]"
        >
          Return to base
        </Link>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error(error);
  const router = useRouter();
  useEffect(() => {
    reportLovableError(error, { boundary: "tanstack_root_error_component" });
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <span className="mono text-[11px] uppercase tracking-[0.3em] text-destructive">
          SYSTEM / FAULT
        </span>
        <h1 className="mt-3 font-display text-3xl font-semibold">
          This page didn't load
        </h1>
        <p className="mt-3 text-sm text-muted-foreground">
          Something ruptured on our end. Try again or head back to base.
        </p>
        <div className="mt-6 flex justify-center gap-2">
          <button
            onClick={() => {
              router.invalidate();
              reset();
            }}
            className="inline-flex items-center rounded-md bg-molten px-4 py-2 text-sm font-medium text-primary-foreground shadow-[var(--shadow-glow)]"
          >
            Retry
          </button>
          <a
            href="/"
            className="inline-flex items-center rounded-md border border-hairline bg-background px-4 py-2 text-sm font-medium text-foreground hover:bg-accent/10"
          >
            Home
          </a>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "GTI HR Portal — GAIL Training Institute" },
      {
        name: "description",
        content:
          "The enterprise HR intelligence portal for the GAIL Training Institute — query employees, teams, events, and update records with a natural-language AI agent.",
      },
      { name: "author", content: "GAIL Training Institute" },
      { property: "og:title", content: "GTI HR Portal — GAIL Training Institute" },
      {
        property: "og:description",
        content:
          "Query, ingest and update HR data at GTI through a modern industrial-futurist workspace.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
    links: [
      { rel: "stylesheet", href: appCss },
      { rel: "icon", type: "image/jpg", href: gailEmblem },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      {
        rel: "preconnect",
        href: "https://fonts.gstatic.com",
        crossOrigin: "anonymous",
      },
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap",
      },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  return (
    <QueryClientProvider client={queryClient}>
      <Outlet />
      <Toaster richColors position="top-right" theme="dark" />
    </QueryClientProvider>
  );
}
