import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { UploadCloud, Trash2, Loader2 } from "lucide-react";
import {
  FormPanel,
  FieldLabel,
  TextField,
} from "@/components/form-panel";
import { ingestEmployee, deleteEmployee } from "@/lib/mock-handlers";

export const Route = createFileRoute("/portal/add/employees")({
  head: () => ({
    meta: [
      { title: "Manage Employees · GTI Portal" },
      { name: "description", content: "Ingest or delete employee records at GTI." },
    ],
  }),
  component: EmployeesForm,
});

function EmployeesForm() {
  const [folder, setFolder] = useState("");
  const [busy, setBusy] = useState<"ingest" | "delete" | null>(null);

  async function run(kind: "ingest" | "delete") {
    if (!folder.trim()) {
      toast.error("Enter an employee folder / ID first.");
      return;
    }
    setBusy(kind);
    const res =
      kind === "ingest"
        ? await ingestEmployee(folder.trim())
        : await deleteEmployee(folder.trim());
    setBusy(null);
    if (res.status === "success") toast.success(res.message);
    else toast.error(res.message);
  }

  return (
    <FormPanel
      title="Manage Employees"
      subtitle="Ingest a folder of employee documents into the vector index, or purge existing records."
      tag="ADD DATA / 01 · EMPLOYEES"
    >
      <div className="space-y-5">
        <div>
          <FieldLabel htmlFor="folder" hint="e.g. EMP-101">
            Employee folder / ID
          </FieldLabel>
          <TextField
            id="folder"
            value={folder}
            onChange={setFolder}
            placeholder="EMP-101"
            disabled={!!busy}
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <ActionButton
            primary
            busy={busy === "ingest"}
            onClick={() => run("ingest")}
            icon={<UploadCloud className="h-4 w-4" />}
          >
            Ingest employee data
          </ActionButton>
          <ActionButton
            busy={busy === "delete"}
            onClick={() => run("delete")}
            icon={<Trash2 className="h-4 w-4" />}
          >
            Delete employee
          </ActionButton>
        </div>

        <p className="mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
          ◇ Ensure documents are placed under <span className="text-cyan">employees/&lt;ID&gt;/</span> before ingesting.
        </p>
      </div>
    </FormPanel>
  );
}

function ActionButton({
  onClick,
  busy,
  icon,
  primary,
  children,
}: {
  onClick: () => void;
  busy: boolean;
  icon: React.ReactNode;
  primary?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      disabled={busy}
      className={
        primary
          ? "flex items-center justify-center gap-2 rounded-md bg-molten px-4 py-3 text-sm font-semibold text-primary-foreground shadow-[var(--shadow-glow)] transition hover:brightness-110 disabled:opacity-60"
          : "flex items-center justify-center gap-2 rounded-md border border-hairline bg-background/60 px-4 py-3 text-sm font-medium text-foreground transition hover:border-destructive hover:text-destructive disabled:opacity-60"
      }
    >
      {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : icon}
      {children}
    </button>
  );
}
