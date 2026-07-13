import { createFileRoute } from "@tanstack/react-router";
import { ChatSurface } from "@/components/chat-surface";
import { querySingleEmployee } from "@/lib/mock-handlers";

export const Route = createFileRoute("/portal/query/single")({
  head: () => ({
    meta: [
      { title: "Single Employee Query · GTI Portal" },
      {
        name: "description",
        content: "Chat with the GTI HR assistant about a single employee's profile.",
      },
    ],
  }),
  component: () => (
    <ChatSurface
      title="Single Employee Profile"
      subtitle="Ask anything about one employee — profile, leave, reporting line, training."
      greeting="Hello. I'm your **Single Profile Agent**. Give me an employee name or ID (e.g. `EMP-101`) and what you'd like to know."
      suggestions={[
        "Show Aditya's leave balance",
        "Who does EMP-042 report to?",
        "Training history for EMP-101",
      ]}
      onSend={querySingleEmployee}
    />
  ),
});
