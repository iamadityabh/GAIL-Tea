import { createFileRoute } from "@tanstack/react-router";
import { ChatSurface } from "@/components/chat-surface";
import { queryOverall } from "@/lib/mock-handlers";

export const Route = createFileRoute("/portal/query/overall")({
  head: () => ({
    meta: [
      { title: "Team & Company Query · GTI Portal" },
      {
        name: "description",
        content: "Company-wide HR analytics for GAIL Training Institute.",
      },
    ],
  }),
  component: () => (
    <ChatSurface
      title="Team & Company-wide"
      subtitle="Aggregate signals across departments — headcount, attrition, trends."
      greeting="Hi. I'm your **Overall Analytics Agent**. Ask me about company-wide or departmental metrics."
      accent="cyan"
      suggestions={[
        "Total No. Of departments",
        "List all the employees and there project names",
        "List all the employees with age above 20",
      ]}
      onSend={queryOverall}
    />
  ),
});
