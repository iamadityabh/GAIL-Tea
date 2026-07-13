import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { UploadCloud, Trash2, Loader2 } from "lucide-react";
import { FormPanel, FieldLabel, TextField } from "@/components/form-panel";
import { ingestEvent, deleteEvent } from "@/lib/mock-handlers";

export const Route = createFileRoute("/portal/add/events")({
  head: () => ({
    meta: [
      { title: "Manage Events · GTI Portal" },
      { name: "description", content: "Ingest event PDFs and TXT files or delete an event." },
    ],
  }),
  component: EventsForm,
});

function EventsForm() {
  const [eventId, setEventId] = useState("");
  const [busy, setBusy] = useState<"ingest" | "delete" | null>(null);

  async function run(kind: "ingest" | "delete") {
    if (!eventId.trim()) {
      toast.error("Enter an event ID first.");
      return;
    }
    setBusy(kind);
    const res =
      kind === "ingest"
        ? await ingestEvent(eventId.trim())
        : await deleteEvent(eventId.trim());
    setBusy(null);
    res.status === "success" ? toast.success(res.message) : toast.error(res.message);
  }

  return (
    <FormPanel
      title="Manage Events"
      subtitle="Extract and index event PDFs and TXT files, or purge an event's records."
      tag="ADD DATA / 03 · EVENTS"
    >
      <div className="space-y-5">
        <div className="mono rounded-md border border-hairline bg-background/40 px-4 py-3 text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
          ◇ Place event PDFs and TXT files in{" "}
          <span className="text-cyan">events/&lt;Event-ID&gt;/</span> before ingesting.
        </div>
        <div>
          <FieldLabel htmlFor="ev-id" hint="e.g. EVT-01">
            Event folder / ID
          </FieldLabel>
          <TextField
            id="ev-id"
            value={eventId}
            onChange={setEventId}
            placeholder="EVT-01"
            disabled={!!busy}
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <button
            onClick={() => run("ingest")}
            disabled={busy === "ingest"}
            className="flex items-center justify-center gap-2 rounded-md bg-molten px-4 py-3 text-sm font-semibold text-primary-foreground shadow-[var(--shadow-glow)] transition hover:brightness-110 disabled:opacity-60"
          >
            {busy === "ingest" ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
            Ingest event data
          </button>
          <button
            onClick={() => run("delete")}
            disabled={busy === "delete"}
            className="flex items-center justify-center gap-2 rounded-md border border-hairline bg-background/60 px-4 py-3 text-sm font-medium text-foreground transition hover:border-destructive hover:text-destructive disabled:opacity-60"
          >
            {busy === "delete" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
            Delete event
          </button>
        </div>
      </div>
    </FormPanel>
  );
}
