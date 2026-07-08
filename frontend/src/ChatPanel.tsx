import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Button } from "./components/ui/button";
import { Input } from "./components/ui/input";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Props {
  messages: Message[];
  onSend: (text: string) => Promise<void>;
  loading: boolean;
  collapsed: boolean;
  onToggle: () => void;
}

export function ChatPanel({ messages, onSend, loading, collapsed, onToggle }: Props) {
  const [input, setInput] = useState("");
  const [width, setWidth] = useState(320);
  const listRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef(false);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!input.trim() || loading) return;
      const text = input.trim();
      setInput("");
      await onSend(text);
    },
    [input, loading, onSend],
  );

  useEffect(() => {
    if (!listRef.current) return;
    listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages]);

  // ── Resize ────────────────────────────────────────────────────────────────
  const handleMouseDown = useCallback(() => {
    draggingRef.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!draggingRef.current) return;
      setWidth(Math.max(280, Math.min(500, window.innerWidth - e.clientX)));
    };
    const handleMouseUp = () => {
      draggingRef.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);

  if (collapsed) {
    return (
      <div className="border-l bg-card flex flex-col items-center pt-4" style={{ width: 48, flexShrink: 0 }}>
        <Button variant="ghost" size="icon" onClick={onToggle} title="Abrir chat">
          💬
        </Button>
      </div>
    );
  }

  return (
    <div className="border-l bg-card flex flex-col relative" style={{ width, flexShrink: 0 }}>
      {/* Drag handle */}
      <div
        onMouseDown={handleMouseDown}
        className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-primary/50 transition-colors z-10"
      />

      <div className="flex items-center justify-between p-3 pb-0">
        <strong className="text-sm">Chat</strong>
        <Button variant="ghost" size="icon" onClick={onToggle} title="Cerrar chat">
          ✕
        </Button>
      </div>

      <div ref={listRef} className="flex-1 overflow-y-auto px-3 py-2 space-y-2">
          {messages.length === 0 && (
            <p className="text-xs text-muted-foreground text-center mt-6">
              Pregunta sobre tu factura o conceptos eléctricos.
            </p>
          )}
          {messages.map((m, i) => (
            <div
              key={i}
              className={`rounded-xl px-3 py-2 text-sm leading-relaxed max-w-[88%] ${
                m.role === "user"
                  ? "bg-primary text-primary-foreground self-end"
                  : "bg-muted self-start"
              }`}
            >
              {m.role === "assistant" ? (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    p: ({ children }) => <p className="mb-1.5 last:mb-0">{children}</p>,
                    strong: ({ children }) => <strong>{children}</strong>,
                    code: ({ children }) => (
                      <code className="text-xs bg-muted-foreground/20 px-1 py-0.5 rounded">
                        {children}
                      </code>
                    ),
                    ul: ({ children }) => <ul className="my-1 pl-4">{children}</ul>,
                    li: ({ children }) => <li className="mb-0.5">{children}</li>,
                  }}
                >
                  {m.content}
                </ReactMarkdown>
              ) : (
                m.content
              )}
            </div>
          ))}
          {loading && (
            <div className="rounded-xl px-3 py-2 text-sm bg-muted self-start text-muted-foreground">
              Pensando…
            </div>
          )}
        </div>

      <form onSubmit={handleSubmit} className="flex gap-2 p-3 pt-0">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Escribe una pregunta…"
          disabled={loading}
          className="text-sm"
        />
        <Button type="submit" size="sm" disabled={loading || !input.trim()}>
          Enviar
        </Button>
      </form>
    </div>
  );
}
