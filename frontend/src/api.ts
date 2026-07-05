export interface HourlyPrice {
  hour: number;
  price: number;
}

export interface PricesResponse {
  pvpc: {
    today: HourlyPrice[];
    tomorrow: HourlyPrice[] | null;
  };
  omie: {
    today: HourlyPrice[];
    tomorrow: HourlyPrice[] | null;
  };
  currency: string;
  unit: string;
}

export interface Finding {
  code: string;
  severity: "critical" | "warning" | "info";
  titulo: string;
  detalle: string;
  ahorro_estimado_eur_mes: number | null;
}

export interface AnalyzeResponse {
  factura: Record<string, unknown>;
  findings: Finding[];
}

export interface ChatRequest {
  messages: { role: string; content: string }[];
  factura?: Record<string, unknown> | null;
  prices?: PricesResponse | null;
}

export interface ChatResponse {
  answer: string;
}

export async function fetchPrices(): Promise<PricesResponse> {
  const res = await fetch("/api/prices");
  if (!res.ok) throw new Error(`Error al cargar precios: ${res.status}`);
  return res.json();
}

export async function analyzePDF(file: File): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("pdf", file);
  const res = await fetch("/api/analyze", { method: "POST", body: form });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Error: ${res.status}`);
  }
  return res.json();
}

export async function chat(req: ChatRequest): Promise<ChatResponse> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`Error: ${res.status}`);
  return res.json();
}
