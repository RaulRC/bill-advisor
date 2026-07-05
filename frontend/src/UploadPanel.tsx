import { type DragEvent, useRef, useState } from "react";

interface Props {
  onFile: (file: File) => void;
  loading: boolean;
}

export function UploadPanel({ onFile, loading }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleFile = (f: File) => {
    if (f.type === "application/pdf" || f.name.endsWith(".pdf")) {
      onFile(f);
    }
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const onDragOver = (e: DragEvent) => {
    e.preventDefault();
    setDragging(true);
  };
  const onDragLeave = () => setDragging(false);

  return (
    <div
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onClick={() => inputRef.current?.click()}
      style={{
        border: `2px dashed ${dragging ? "#2563eb" : "#d1d5db"}`,
        borderRadius: 12,
        padding: "40px 24px",
        textAlign: "center",
        cursor: "pointer",
        background: dragging ? "#eff6ff" : "#f9fafb",
        transition: "all 0.15s",
        opacity: loading ? 0.5 : 1,
        pointerEvents: loading ? "none" : "auto",
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,application/pdf"
        hidden
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
        }}
      />
      <div style={{ fontSize: 32, marginBottom: 8 }}>
        {loading ? "⏳" : "📄"}
      </div>
      {loading ? (
        <p style={{ margin: 0, color: "#666" }}>Analizando factura…</p>
      ) : (
        <>
          <p style={{ margin: "0 0 4px", fontWeight: 600, color: "#333" }}>
            Sube tu factura de la luz
          </p>
          <p style={{ margin: 0, fontSize: 13, color: "#888" }}>
            Arrastra un PDF o haz clic para seleccionar
          </p>
        </>
      )}
    </div>
  );
}
