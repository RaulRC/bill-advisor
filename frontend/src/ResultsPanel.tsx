import { useState } from "react";
import type { AnalyzeResponse, Finding } from "./api";

interface Props {
  data: AnalyzeResponse;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: "#dc2626",
  warning: "#d97706",
  info: "#2563eb",
};

const SEVERITY_LABELS: Record<string, string> = {
  critical: "Crítico",
  warning: "Advertencia",
  info: "Información",
};

function FindingCard({ f }: { f: Finding }) {
  const [open, setOpen] = useState(false);

  return (
    <div
      onClick={() => setOpen((o) => !o)}
      style={{
        borderLeft: `4px solid ${SEVERITY_COLORS[f.severity]}`,
        padding: "12px 16px",
        marginBottom: 8,
        background: "#f9fafb",
        borderRadius: "0 8px 8px 0",
        cursor: "pointer",
        userSelect: "none",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <strong style={{ fontSize: 14 }}>{open ? "▼" : "▶"} {f.titulo}</strong>
        <span
          style={{
            fontSize: 11,
            color: SEVERITY_COLORS[f.severity],
            fontWeight: 600,
          }}
        >
          {SEVERITY_LABELS[f.severity]}
        </span>
      </div>
      {open && (
        <>
          <p style={{ margin: "8px 0 0", fontSize: 13, color: "#555", lineHeight: 1.4 }}>
            {f.descripcion}
          </p>
          {f.ahorro_estimado_eur_mes != null && (
            <p style={{ margin: "6px 0 0", fontSize: 13, fontWeight: 600, color: "#059669" }}>
              Ahorro estimado: {f.ahorro_estimado_eur_mes.toFixed(0)} €/mes
            </p>
          )}
        </>
      )}
    </div>
  );
}

export function ResultsPanel({ data }: Props) {
  const f = data.factura as Record<string, any>;
  const contrato = f.contrato ?? {};
  const energia = f.energia ?? {};
  const totales = f.totales ?? {};
  const periodo = f.periodo ?? {};

  return (
    <div>
      <h3 style={{ margin: "0 0 12px", fontSize: 16 }}>Resumen de la factura</h3>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 8,
          fontSize: 13,
          marginBottom: 16,
        }}
      >
        <InfoRow label="Comercializadora" value={contrato.comercializadora} />
        <InfoRow label="Modalidad" value={contrato.modalidad} />
        <InfoRow label="Periodo" value={`${periodo.fecha_inicio} → ${periodo.fecha_fin}`} />
        <InfoRow label="Consumo" value={`${energia.kwh_total?.toFixed(0) ?? "—"} kWh`} />
        <InfoRow label="Potencia" value={`${f.potencia?.potencia_contratada_kw ?? "—"} kW`} />
        <InfoRow label="Total" value={`${totales.total_factura_eur?.toFixed(2) ?? "—"} €`} />
      </div>

      <h3 style={{ margin: "0 0 8px", fontSize: 16 }}>
        Auditoría ({data.findings.length} hallazgos)
      </h3>
      {data.findings.map((f) => (
        <FindingCard key={f.code} f={f} />
      ))}
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div>
      <span style={{ color: "#888" }}>{label}</span>
      <br />
      <span style={{ fontWeight: 600 }}>{value ?? "—"}</span>
    </div>
  );
}
