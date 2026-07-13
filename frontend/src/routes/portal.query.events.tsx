import { createFileRoute } from "@tanstack/react-router";
import { ChatSurface } from "@/components/chat-surface";
import { queryEvents } from "@/lib/mock-handlers";

export const Route = createFileRoute("/portal/query/events")({
  head: () => ({
    meta: [
      { title: "Events Query · GTI Portal" },
      {
        name: "description",
        content: "Ask about GTI training events, attendees and schedules.",
      },
    ],
  }),
  component: () => (
    <ChatSurface
      title="Event Related Query"
      subtitle="Search training events, attendees, dates, venues and feedback."
      greeting="Ready. I'm your **Events Agent** — ask about any `EVT-ID`, upcoming sessions, or historic attendance."
      accent="cyan"
      suggestions={[
        "Upcoming training in December",
        "Attendees of EVT-01",
        "Feedback for last month's sessions",
      ]}
      onSend={queryEvents}
    />
  ),
});
