import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import ReactMarkdown from "react-markdown";
import { Send } from "lucide-react";

type Msg = { role: "user" | "assistant"; content: string };

type Props = {
  title: string;
  subtitle: string;
  greeting: string;
  suggestions: string[];
  onSend: (text: string) => Promise<{ markdown: string }>;
  accent?: "molten" | "cyan";
};

export function ChatSurface({
  title,
  subtitle,
  greeting,
  suggestions,
  onSend,
  accent = "molten",
}: Props) {
  const [messages, setMessages] = useState<Msg[]>([
    { role: "assistant", content: greeting },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, busy]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  async function submit(text: string) {
    const value = text.trim();
    if (!value || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: value }]);
    setBusy(true);
    try {
      const { markdown } = await onSend(value);
      setMessages((m) => [...m, { role: "assistant", content: markdown }]);
    } finally {
      setBusy(false);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }

  const accentClass =
    accent === "cyan"
      ? "from-cyan/40 to-cyan/0 text-cyan"
      : "from-molten/40 to-molten/0 text-molten";
  const accentBg =
    accent === "cyan" ? "bg-cyan text-background" : "bg-molten text-primary-foreground";

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      {/* Header */}
      <div className="border-b border-hairline px-6 py-4">
        <div className="flex items-center gap-3">
          <span className="mono text-[10px] uppercase tracking-[0.25em] text-molten">
            ● Online
          </span>
          <span className="mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground">
            GTI-AGENT / v1.0
          </span>
        </div>
        <h1 className="mt-2 text-2xl font-semibold text-foreground">{title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-6 py-8"
      >
        <div className="mx-auto flex max-w-3xl flex-col gap-6">
          <AnimatePresence initial={false}>
            {messages.map((m, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
                className={
                  m.role === "user"
                    ? "flex justify-end"
                    : "flex justify-start"
                }
              >
                {m.role === "user" ? (
                  <div className={`${accentBg} max-w-[75%] rounded-2xl rounded-br-sm px-4 py-3 text-sm font-medium shadow-[var(--shadow-glow)]`}>
                    {m.content}
                  </div>
                ) : (
                  <div className="flex max-w-full flex-col gap-2">
                    <span className="mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground">
                      ◇ Assistant
                    </span>
                    <div className="prose prose-sm prose-invert max-w-none text-foreground/90
                      prose-headings:font-display prose-headings:text-foreground
                      prose-strong:text-foreground
                      prose-code:mono prose-code:text-cyan prose-code:before:content-none prose-code:after:content-none
                      prose-pre:bg-panel prose-pre:border prose-pre:border-hairline prose-pre:text-foreground
                      prose-table:border prose-table:border-hairline
                      prose-th:border prose-th:border-hairline prose-th:bg-secondary prose-th:px-3 prose-th:py-2 prose-th:text-left
                      prose-td:border prose-td:border-hairline prose-td:px-3 prose-td:py-2
                      prose-a:text-molten">
                      <ReactMarkdown>{m.content}</ReactMarkdown>
                    </div>
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
          {busy && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <span className="mono text-[10px] uppercase tracking-[0.25em]">
                Streaming
              </span>
              <span className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="h-1.5 w-1.5 rounded-full bg-molten"
                    style={{
                      animation: `pulse-dot 1s ease-in-out ${i * 0.15}s infinite`,
                    }}
                  />
                ))}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Suggestions + composer */}
      <div className="border-t border-hairline bg-panel/60 px-6 py-4 backdrop-blur">
        <div className="mx-auto max-w-3xl">
          {suggestions.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-2">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => submit(s)}
                  disabled={busy}
                  className={`group mono text-[11px] uppercase tracking-wider rounded-full border border-hairline bg-gradient-to-r ${accentClass} px-3 py-1.5 transition hover:border-molten hover:bg-molten/10 disabled:opacity-40`}
                >
                  {s}
                </button>
              ))}
            </div>
          )}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              submit(input);
            }}
            className="bracket-panel flex items-end gap-2 rounded-lg border border-hairline bg-background/60 p-2"
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submit(input);
                }
              }}
              rows={1}
              placeholder="Type your query… (Shift+Enter for newline)"
              className="min-h-[40px] max-h-40 flex-1 resize-none bg-transparent px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
            />
            <button
              type="submit"
              disabled={busy || !input.trim()}
              className={`${accentBg} flex h-10 w-10 items-center justify-center rounded-md shadow-[var(--shadow-glow)] transition disabled:opacity-40`}
              aria-label="Send"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
