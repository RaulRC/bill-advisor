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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Skeleton } from "./components/ui/skeleton";

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
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-destructive">Error: {error}</p>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-4 w-64" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[280px] w-full" />
        </CardContent>
      </Card>
    );
  }

  const { points, tomorrowStart } = buildSeries(data);

  if (points.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">No hay datos de precios disponibles.</p>
        </CardContent>
      </Card>
    );
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
    <Card>
      <CardHeader>
        <CardTitle>Precios de la electricidad</CardTitle>
        <CardDescription>
          {formatDate(new Date())} — PVPC (regulado) vs OMIE (mercado mayorista)
        </CardDescription>
      </CardHeader>
      <CardContent>
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

        <div className="flex gap-6 text-xs mt-2">
          <span>
            <span className="text-blue-600 font-semibold">━</span> PVPC{" "}
            {todayLabel}
          </span>
          <span>
            <span className="text-amber-600 font-semibold">━</span> OMIE{" "}
            {todayLabel}
          </span>
          {hasTomorrow && (
            <>
              <span className="text-muted-foreground">
                ┊ {tomorrowStart}h de mañana
              </span>
              <span className="text-xs text-muted-foreground">
                (precios previstos)
              </span>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
