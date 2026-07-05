import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { PricesResponse } from "./api";

interface ChartPoint {
  hour: number;
  label: string;
  pvpc: number | null;
  omie: number | null;
  isTomorrow: boolean;
}

function buildSeries(data: PricesResponse): {
  points: ChartPoint[];
  tomorrowStart: number;
} {
  const points: ChartPoint[] = [];

  const today = data.pvpc.today;
  const tomorrow = data.pvpc.tomorrow ?? [];

  for (const h of today) {
    const omie = data.omie.today.find((o) => o.hour === h.hour);
    points.push({
      hour: h.hour,
      label: `${h.hour}:00`,
      pvpc: h.price,
      omie: omie?.price ?? null,
      isTomorrow: false,
    });
  }

  const tomorrowStart = points.length;
  for (const h of tomorrow) {
    const omie = data.omie.tomorrow?.find((o) => o.hour === h.hour);
    points.push({
      hour: h.hour,
      label: `${h.hour}:00`,
      pvpc: h.price,
      omie: omie?.price ?? null,
      isTomorrow: true,
    });
  }

  return { points, tomorrowStart };
}

function fmtEur(v: number) {
  return `${v.toFixed(2)} €/MWh`;
}

interface Props {
  data: PricesResponse | null;
  error: string | null;
}

export function PriceChart({ data, error }: Props) {
  if (error) {
    return <p style={{ color: "#b91c1c" }}>Error: {error}</p>;
  }

  if (!data) {
    return <p>Cargando precios...</p>;
  }

  const { points, tomorrowStart } = buildSeries(data);

  if (points.length === 0) {
    return <p>No hay datos de precios disponibles.</p>;
  }

  const maxPrice = Math.max(
    ...points.map((p) => Math.max(p.pvpc ?? 0, p.omie ?? 0)),
    10,
  );

  const hasTomorrow = tomorrowStart < points.length;
  const todayLabel = `Hoy, ${data.pvpc.today.length}h`;

  const formatDate = (d: Date) =>
    d.toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" });

  return (
    <div>
      <h2 style={{ margin: "0 0 4px 0", fontSize: 18 }}>
        Precios de la electricidad
      </h2>
      <p style={{ margin: "0 0 12px 0", fontSize: 13, color: "#666" }}>
        {formatDate(new Date())} — PVPC (regulado) vs OMIE (mercado mayorista)
      </p>

      <AreaChart
        width={700}
        height={280}
        data={points}
        margin={{ top: 8, right: 16, bottom: 4, left: 8 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11 }}
          interval={2}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          domain={[0, Math.ceil(maxPrice / 50) * 50 + 50]}
          tickFormatter={(v) => `${v}`}
          width={50}
        />
        <Tooltip
          formatter={(v: number, name: string) => [
            fmtEur(v),
            name === "pvpc" ? "PVPC" : "OMIE",
          ]}
          labelFormatter={(label) => label}
        />
        <Area
          type="monotone"
          dataKey="pvpc"
          name="pvpc"
          stroke="#2563eb"
          fill="#2563eb"
          fillOpacity={0.12}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
        <Area
          type="monotone"
          dataKey="omie"
          name="omie"
          stroke="#d97706"
          fill="#d97706"
          fillOpacity={0.08}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
        {hasTomorrow && (
          <ReferenceLine
            x={tomorrowStart - 0.5}
            stroke="#9ca3af"
            strokeDasharray="6 4"
            strokeWidth={1.5}
          />
        )}
      </AreaChart>

      <div style={{ display: "flex", gap: 24, fontSize: 13, marginTop: 8 }}>
        <span>
          <span style={{ color: "#2563eb", fontWeight: 600 }}>━</span> PVPC{" "}
          {todayLabel}
        </span>
        <span>
          <span style={{ color: "#d97706", fontWeight: 600 }}>━</span> OMIE{" "}
          {todayLabel}
        </span>
        {hasTomorrow && (
          <>
            <span style={{ color: "#9ca3af" }}>
              ┊ {tomorrowStart}h de mañana
            </span>
            <span style={{ fontSize: 11, color: "#999" }}>
              (precios previstos)
            </span>
          </>
        )}
      </div>
    </div>
  );
}
