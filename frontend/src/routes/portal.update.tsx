import { createFileRoute } from "@tanstack/react-router";
import { ChatSurface } from "@/components/chat-surface";
import { updateAgent } from "@/lib/mock-handlers";

export const Route = createFileRoute("/portal/update")({
  head: () => ({
    meta: [
      { title: "AI Update Agent · GTI Portal" },
      {
        name: "description",
        content: "Modify HR records in natural language — the agent drafts the SQL.",
      },
    ],
  }),
  component: () => (
    <ChatSurface
      title="AI Update Agent"
      subtitle="Describe the change in natural language. I'll draft the SQL and wait for your confirmation."
      greeting="Hello. I'm your **Database Agent**. Describe what you'd like to modify — e.g. `Update Aditya's phone to 98765` — and I'll prepare the query."
      suggestions={[
        "Update Aditya's phone to 98765",
        "Change IT dept head to Ms. Aditi",
        "Set EMP-042 designation to Lead Engineer",
      ]}
      onSend={updateAgent}
    />
  ),
});
