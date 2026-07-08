import { type DragEvent, useRef, useState } from "react";

import { Card, CardContent } from "./components/ui/card";

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
    <Card
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onClick={() => !loading && inputRef.current?.click()}
      className={`cursor-pointer transition-all duration-150 ${
        dragging ? "border-primary bg-blue-50" : ""
      } ${loading ? "pointer-events-none opacity-50" : "hover:border-primary/50"}`}
    >
      <CardContent className="flex flex-col items-center gap-2 py-10">
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
        <span className="text-3xl">{loading ? "⏳" : "📄"}</span>
        {loading ? (
          <p className="text-sm text-muted-foreground">Analizando factura…</p>
        ) : (
          <>
            <p className="font-semibold text-sm">Sube tu factura de la luz</p>
            <p className="text-xs text-muted-foreground">
              Arrastra un PDF o haz clic para seleccionar
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
