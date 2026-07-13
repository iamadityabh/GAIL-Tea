import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { Plus, Trash2, Loader2 } from "lucide-react";
import {
  FormPanel,
  FieldLabel,
  TextField,
} from "@/components/form-panel";
import { addDepartment, deleteDepartment } from "@/lib/mock-handlers";

export const Route = createFileRoute("/portal/add/departments")({
  head: () => ({
    meta: [
      { title: "Manage Departments · GTI Portal" },
      { name: "description", content: "Add or delete GTI departments with cache sync." },
    ],
  }),
  component: DepartmentsForm,
});

function DepartmentsForm() {
  const [id, setId] = useState("");
  const [name, setName] = useState("");
  const [head, setHead] = useState("");
  const [landline, setLandline] = useState("");
  const [busy, setBusy] = useState<"add" | "delete" | null>(null);

  async function add() {
    setBusy("add");
    const res = await addDepartment(id.trim(), name.trim());
    setBusy(null);
    res.status === "success" ? toast.success(res.message) : toast.error(res.message);
  }
  async function remove() {
    setBusy("delete");
    const res = await deleteDepartment(id.trim());
    setBusy(null);
    res.status === "success" ? toast.success(res.message) : toast.error(res.message);
  }

  return (
    <FormPanel
      title="Manage Departments"
      subtitle="Add a new department or remove one. The department cache is synced automatically."
      tag="ADD DATA / 02 · DEPARTMENTS"
    >
      <div className="grid gap-5 sm:grid-cols-2">
        <div>
          <FieldLabel htmlFor="d-id" hint="e.g. D-01">
            Department ID
          </FieldLabel>
          <TextField id="d-id" value={id} onChange={setId} placeholder="D-01" disabled={!!busy} />
        </div>
        <div>
          <FieldLabel htmlFor="d-name">Department name</FieldLabel>
          <TextField id="d-name" value={name} onChange={setName} placeholder="HR & Training" disabled={!!busy} />
        </div>
        <div>
          <FieldLabel htmlFor="d-head">Head of department</FieldLabel>
          <TextField id="d-head" value={head} onChange={setHead} placeholder="Mr. Sharma" disabled={!!busy} />
        </div>
        <div>
          <FieldLabel htmlFor="d-ext" hint="3–4 digits">
            Landline extension
          </FieldLabel>
          <TextField id="d-ext" value={landline} onChange={setLandline} placeholder="4012" disabled={!!busy} />
        </div>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        <button
          onClick={add}
          disabled={busy === "add"}
          className="flex items-center justify-center gap-2 rounded-md bg-molten px-4 py-3 text-sm font-semibold text-primary-foreground shadow-[var(--shadow-glow)] transition hover:brightness-110 disabled:opacity-60"
        >
          {busy === "add" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          Add department
        </button>
        <button
          onClick={remove}
          disabled={busy === "delete"}
          className="flex items-center justify-center gap-2 rounded-md border border-hairline bg-background/60 px-4 py-3 text-sm font-medium text-foreground transition hover:border-destructive hover:text-destructive disabled:opacity-60"
        >
          {busy === "delete" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          Delete department
        </button>
      </div>
    </FormPanel>
  );
}
