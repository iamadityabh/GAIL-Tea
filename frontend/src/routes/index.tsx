import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "motion/react";
import { ArrowRight, MessageSquare, Database, Wand2 } from "lucide-react";

import gailEmblem from "@/assets/gail-emblem.jpg";

export const Route = createFileRoute("/")({
  component: Landing,
});

const stats = [
  { k: "311", l: "Employees indexed" },
  { k: "5", l: "Departments" },
  { k: "48", l: "Training events" },
  { k: "1,284", l: "Queries answered · 30d" },
  { k: "99.98%", l: "Agent uptime" },
];

const entries = [
  {
    to: "/portal/query/single",
    title: "Ask a Query",
    desc: "Chat with an assistant across employee, team and event data.",
    icon: MessageSquare,
    tag: "MODE / 01",
  },
  {
    to: "/portal/add/employees",
    title: "Add Data",
    desc: "Ingest employees, manage departments and index event PDFs.",
    icon: Database,
    tag: "MODE / 02",
  },
  {
    to: "/portal/update",
    title: "Update Data",
    desc: "Modify records in natural language — the agent writes the SQL.",
    icon: Wand2,
    tag: "MODE / 03",
  },
] as const;

function Landing() {
  return (
    <div className="noise relative min-h-screen overflow-hidden bg-background text-foreground">
      {/* animated pipeline grid */}
      <div className="grid-bg absolute inset-0 opacity-60" aria-hidden />
      <div
        className="pointer-events-none absolute -top-40 left-1/2 h-[600px] w-[900px] -translate-x-1/2 rounded-full opacity-40 blur-3xl"
        style={{ background: "var(--gradient-pipeline)" }}
        aria-hidden
      />
      <PipelineSvg />

      {/* Top bar */}
      <header className="relative z-10 mx-auto flex max-w-7xl items-center justify-between px-6 py-6">
        <div className="flex min-w-0 items-center gap-4">
          <span className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-molten/10 p-2 ring-1 ring-molten/30 shadow-[var(--shadow-glow)]">
            <img
              src={gailEmblem}
              alt="GAIL logo"
              className="h-full w-full object-contain"
            />
          </span>
          <div className="flex min-w-0 flex-col leading-none">
            <span className="font-display text-lg font-semibold tracking-tight">
              GTI PORTAL
            </span>
            <span className="mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground">
              GAIL Training Institute
            </span>
          </div>
        </div>
        <nav className="mono hidden items-center gap-6 text-[11px] uppercase tracking-[0.2em] text-muted-foreground md:flex">
          <a href="#modes" className="hover:text-molten">Modes</a>
          <a href="#stats" className="hover:text-molten">Signals</a>
          <span className="rounded-full border border-hairline px-2 py-0.5 text-molten">
            ● v1.0 online
          </span>
        </nav>
      </header>

      {/* Hero */}
      <section className="relative z-10 mx-auto max-w-7xl px-6 pb-16 pt-16 md:pt-24">
        <motion.span
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="mono inline-block rounded-full border border-hairline bg-panel/50 px-3 py-1 text-[10px] uppercase tracking-[0.3em] text-molten backdrop-blur"
        >
          ● Enterprise HR intelligence · GTI
        </motion.span>
        <motion.h1
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="mt-6 font-display text-5xl font-semibold leading-[0.95] tracking-tight md:text-7xl lg:text-8xl"
        >
          The command room{" "}
          <span className="bg-clip-text text-transparent" style={{ backgroundImage: "var(--gradient-pipeline)" }}>
            for GTI's people.
          </span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.12 }}
          className="mt-6 max-w-2xl text-base text-muted-foreground md:text-lg"
        >
          Query, ingest and update employee, department and event data across the
          GAIL Training Institute — through a natural-language workspace built
          for operations that don't sleep.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mt-10 flex flex-wrap items-center gap-3"
        >
          <Link
            to="/portal/query/single"
            className="group relative inline-flex items-center gap-2 rounded-md bg-molten px-5 py-3 text-sm font-semibold text-primary-foreground shadow-[var(--shadow-glow)] transition hover:brightness-110"
          >
            Enter portal
            <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
          </Link>
          <a
            href="#modes"
            className="mono rounded-md border border-hairline bg-panel/60 px-5 py-3 text-[11px] uppercase tracking-[0.2em] text-foreground backdrop-blur hover:border-molten hover:text-molten"
          >
            See operating modes
          </a>
        </motion.div>
      </section>

      {/* Ticker */}
      <section id="stats" className="relative z-10 border-y border-hairline bg-panel/40 backdrop-blur">
        <div className="flex overflow-hidden">
          <div className="animate-[marquee_40s_linear_infinite] flex shrink-0 gap-14 whitespace-nowrap px-6 py-4">
            {[...stats, ...stats, ...stats].map((s, i) => (
              <span key={i} className="mono flex items-center gap-3 text-[11px] uppercase tracking-[0.25em] text-muted-foreground">
                <span className="text-molten">◇</span>
                <span className="text-foreground">{s.k}</span>
                <span>{s.l}</span>
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Modes */}
      <section id="modes" className="relative z-10 mx-auto max-w-7xl px-6 py-24">
        <div className="mb-10 flex items-end justify-between">
          <div>
            <span className="mono text-[11px] uppercase tracking-[0.3em] text-molten">
              // Operating modes
            </span>
            <h2 className="mt-3 font-display text-3xl font-semibold md:text-4xl">
              Three surfaces. One nervous system.
            </h2>
          </div>
          <span className="mono hidden text-[10px] uppercase tracking-[0.3em] text-muted-foreground md:block">
            003 · endpoints
          </span>
        </div>
        <div className="grid gap-5 md:grid-cols-3">
          {entries.map((e, i) => (
            <motion.div
              key={e.to}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
            >
              <Link
                to={e.to}
                className="bracket-panel group relative flex h-full flex-col justify-between overflow-hidden rounded-lg border border-hairline bg-panel p-6 transition hover:border-molten"
                style={{ backgroundImage: "var(--gradient-panel)" }}
              >
                <div
                  className="pointer-events-none absolute -inset-1 opacity-0 blur-2xl transition group-hover:opacity-40"
                  style={{ background: "var(--gradient-pipeline)" }}
                />
                <div className="relative">
                  <div className="flex items-center justify-between">
                    <span className="mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground">
                      {e.tag}
                    </span>
                    <e.icon className="h-5 w-5 text-molten" />
                  </div>
                  <h3 className="mt-8 font-display text-2xl font-semibold">
                    {e.title}
                  </h3>
                  <p className="mt-3 text-sm text-muted-foreground">{e.desc}</p>
                </div>
                <div className="relative mt-8 flex items-center justify-between">
                  <span className="mono text-[11px] uppercase tracking-[0.25em] text-foreground/70 group-hover:text-molten">
                    Open →
                  </span>
                  <span className="h-px w-16 bg-hairline group-hover:bg-molten" />
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-hairline">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-4 px-6 py-8 text-xs text-muted-foreground md:flex-row md:items-center">
          <div className="mono uppercase tracking-[0.25em]">
            © GAIL Training Institute · GTI-HR / mock build
          </div>
          <div className="mono flex gap-4 uppercase tracking-[0.25em]">
            <span>Noida · Vadodara · Virtual</span>
            <span className="text-molten">● all systems nominal</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

function PipelineSvg() {
  return (
    <svg
      className="pointer-events-none absolute inset-x-0 top-32 mx-auto h-[440px] w-full max-w-6xl opacity-30"
      viewBox="0 0 1200 400"
      fill="none"
      aria-hidden
    >
      <defs>
        <linearGradient id="pl" x1="0" x2="1">
          <stop offset="0" stopColor="oklch(0.72 0.19 45)" stopOpacity="0" />
          <stop offset="0.5" stopColor="oklch(0.72 0.19 45)" stopOpacity="1" />
          <stop offset="1" stopColor="oklch(0.82 0.14 195)" stopOpacity="0" />
        </linearGradient>
      </defs>
      {[80, 160, 240, 320].map((y, i) => (
        <motion.path
          key={y}
          d={`M0 ${y} Q 300 ${y - 40} 600 ${y} T 1200 ${y}`}
          stroke="url(#pl)"
          strokeWidth="1"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 3, delay: i * 0.4, ease: "easeInOut" }}
        />
      ))}
      {[[220, 80], [520, 160], [820, 240], [1020, 320]].map(([x, y], i) => (
        <motion.circle
          key={i}
          cx={x}
          cy={y}
          r="3"
          fill="oklch(0.82 0.14 195)"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 2, delay: i * 0.3, repeat: Infinity }}
        />
      ))}
    </svg>
  );
}
