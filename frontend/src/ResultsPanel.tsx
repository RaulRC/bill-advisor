import { useState } from "react";

import type { AnalyzeResponse, Finding } from "./api";
import { Badge } from "./components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { Separator } from "./components/ui/separator";

interface Props {
  data: AnalyzeResponse;
}

const SEVERITY_VARIANT: Record<string, "destructive" | "secondary" | "default"> = {
  critical: "destructive",
  warning: "secondary",
  info: "default",
};

const SEVERITY_LABELS: Record<string, string> = {
  critical: "Crítico",
  warning: "Advertencia",
  info: "Información",
};

function FindingCard({ f }: { f: Finding }) {
  const [open, setOpen] = useState(true);

  return (
    <div
      onClick={() => setOpen((o) => !o)}
      className="border-l-4 cursor-pointer select-none py-3 px-4 rounded-r-lg bg-muted/50 mb-2 transition-colors hover:bg-muted/80"
      style={{ borderLeftColor: f.severity === "critical" ? "#dc2626" : f.severity === "warning" ? "#d97706" : "#2563eb" }}
    >
      <div className="flex items-center justify-between">
        <strong className="text-sm">{open ? "▼" : "▶"} {f.titulo}</strong>
        <Badge variant={SEVERITY_VARIANT[f.severity]}>
          {SEVERITY_LABELS[f.severity]}
        </Badge>
      </div>
      {open && (
        <>
          <p className="text-xs text-muted-foreground mt-2 leading-relaxed">
            {f.detalle}
          </p>
          {f.ahorro_estimado_eur_mes != null && (
            <p className="text-xs font-semibold text-emerald-600 mt-1.5">
              Ahorro estimado: {f.ahorro_estimado_eur_mes.toFixed(0)} €/mes
            </p>
          )}
        </>
      )}
    </div>
  );
}

function _summaryText(f: Record<string, any>) {
  const c = f.contrato ?? {};
  const e = f.energia ?? {};
  const t = f.totales ?? {};
  const p = f.periodo ?? {};
  const pot = f.potencia ?? {};

  const parts: string[] = [
    `Factura de ${c.comercializadora ?? "comercializadora desconocida"}`,
    `con tarifa ${c.modalidad ?? "desconocida"}`,
    p.fecha_inicio && p.fecha_fin
      ? `para el período del ${p.fecha_inicio} al ${p.fecha_fin}`
      : "",
    e.kwh_total != null
      ? `Has consumido ${e.kwh_total.toFixed(0)} kWh`
      : "",
    pot.potencia_contratada_kw != null
      ? `con una potencia contratada de ${pot.potencia_contratada_kw} kW`
      : "",
    t.total_factura_eur != null
      ? `El importe total asciende a ${t.total_factura_eur.toFixed(2)} €`
      : "",
    c.modalidad === "PVPC"
      ? "Al estar en PVPC, tu precio varía cada hora según el mercado."
      : "Revisa las recomendaciones de la auditoría para posibles ahorros.",
  ].filter(Boolean);

  return parts.join(". ") + ".";
}

function InfoRow({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div>
      <span className="text-muted-foreground text-xs">{label}</span>
      <br />
      <span className="font-semibold text-sm">{value ?? "—"}</span>
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
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Resumen de la factura</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm mb-4">
            <InfoRow label="Comercializadora" value={contrato.comercializadora} />
            <InfoRow label="Modalidad" value={contrato.modalidad} />
            <InfoRow label="Periodo" value={`${periodo.fecha_inicio} → ${periodo.fecha_fin}`} />
            <InfoRow label="Consumo" value={`${energia.kwh_total?.toFixed(0) ?? "—"} kWh`} />
            <InfoRow label="Potencia" value={`${f.potencia?.potencia_contratada_kw ?? "—"} kW`} />
            <InfoRow label="Total" value={`${totales.total_factura_eur?.toFixed(2) ?? "—"} €`} />
          </div>

          <div className="bg-primary/5 border-l-4 border-primary rounded-r-lg p-3 text-xs text-muted-foreground leading-relaxed">
            {_summaryText(f)}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Auditoría ({data.findings.length} hallazgos)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {data.findings.map((f, i) => (
            <div key={f.code}>
              <FindingCard f={f} />
              {i < data.findings.length - 1 && <Separator className="my-2" />}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
