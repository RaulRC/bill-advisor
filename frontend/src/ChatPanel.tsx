import { useCallback, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

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
  const listRef = useRef<HTMLDivElement>(null);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!input.trim() || loading) return;
      const text = input.trim();
      setInput("");
      await onSend(text);
      setTimeout(() => {
        listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
      }, 50);
    },
    [input, loading, onSend],
  );

  if (collapsed) {
    return (
      <div style={sidebarStyle}>
        <button onClick={onToggle} style={toggleBtnStyle} title="Abrir chat">
          💬
        </button>
      </div>
    );
  }

  return (
    <div style={sidebarStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <strong style={{ fontSize: 14 }}>Chat</strong>
        <button onClick={onToggle} style={toggleBtnStyle} title="Cerrar chat">
          ✕
        </button>
      </div>

      <div
        ref={listRef}
        style={{
          flex: 1,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 8,
          marginBottom: 8,
        }}
      >
        {messages.length === 0 && (
          <p style={{ fontSize: 13, color: "#888", textAlign: "center", marginTop: 24 }}>
            Pregunta sobre tu factura o conceptos eléctricos.
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              padding: "8px 12px",
              borderRadius: 12,
              fontSize: 13,
              lineHeight: 1.5,
              maxWidth: "88%",
              alignSelf: m.role === "user" ? "flex-end" : "flex-start",
              background: m.role === "user" ? "#2563eb" : "#f3f4f6",
              color: m.role === "user" ? "#fff" : "#333",
            }}
          >
            {m.role === "assistant" ? (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  p: ({ children }) => <p style={{ margin: "0 0 6px" }}>{children}</p>,
                  strong: ({ children }) => <strong style={{ color: "#111" }}>{children}</strong>,
                  code: ({ children }) => (
                    <code style={{ fontSize: 12, background: "#e5e7eb", padding: "1px 4px", borderRadius: 4 }}>
                      {children}
                    </code>
                  ),
                  ul: ({ children }) => <ul style={{ margin: "4px 0", paddingLeft: 16 }}>{children}</ul>,
                  li: ({ children }) => <li style={{ marginBottom: 2 }}>{children}</li>,
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
          <div
            style={{
              padding: "8px 12px",
              borderRadius: 12,
              fontSize: 13,
              alignSelf: "flex-start",
              background: "#f3f4f6",
              color: "#888",
            }}
          >
            Pensando…
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} style={{ display: "flex", gap: 6 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Escribe una pregunta…"
          disabled={loading}
          style={{
            flex: 1,
            padding: "8px 12px",
            borderRadius: 8,
            border: "1px solid #d1d5db",
            fontSize: 13,
            outline: "none",
          }}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          style={{
            padding: "8px 14px",
            borderRadius: 8,
            border: "none",
            background: loading || !input.trim() ? "#d1d5db" : "#2563eb",
            color: "#fff",
            fontSize: 13,
            cursor: loading || !input.trim() ? "default" : "pointer",
          }}
        >
          Enviar
        </button>
      </form>
    </div>
  );
}

const sidebarStyle: React.CSSProperties = {
  width: 320,
  display: "flex",
  flexDirection: "column",
  borderLeft: "1px solid #e5e7eb",
  padding: 16,
  background: "#fff",
  flexShrink: 0,
};

const toggleBtnStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  cursor: "pointer",
  fontSize: 14,
  padding: 4,
  color: "#666",
};
