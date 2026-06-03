from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from bill_advisor.schemas import Factura

# 2.0TD period definitions (hour ranges)
PUNTA_HOURS = set(range(10, 14)) | set(range(18, 22))
LLANO_HOURS = set(range(8, 10)) | set(range(14, 18)) | set(range(22, 24))
VALLE_HOURS = set(range(0, 8))


@dataclass(frozen=True)
class ComparisonResult:
    actual_energy_cost_eur: float
    pvpc_energy_cost_eur: float
    savings_energy_eur: float
    annual_savings_eur: float
    pvpc_is_cheaper: bool
    detail: str


def _is_weekend(d: date) -> bool:
    return d.weekday() >= 5


def _count_period_hours(
    start: date, end: date,
) -> tuple[int, int, int]:
    punta = llano = valle = 0
    current = start
    while current < end:
        if _is_weekend(current):
            valle += 24
        else:
            punta += 8
            llano += 8
            valle += 8
        current += timedelta(days=1)
    return punta, llano, valle


def _get_period(d: date, hour: int) -> str:
    if _is_weekend(d):
        return "valle"
    if hour in PUNTA_HOURS:
        return "punta"
    if hour in LLANO_HOURS:
        return "llano"
    return "valle"


def compare_with_pvpc(
    factura: Factura,
    hourly_prices: dict[date, dict[int, float]],
) -> ComparisonResult | None:
    if factura.contrato.modalidad == "PVPC":
        return None

    start = factura.periodo.fecha_inicio
    end = factura.periodo.fecha_fin
    dias = factura.periodo.dias_facturados
    if dias <= 0:
        return None

    punta_h, llano_h, valle_h = _count_period_hours(start, end)

    kwh_p = factura.energia.kwh_punta
    kwh_l = factura.energia.kwh_llano
    kwh_v = factura.energia.kwh_valle

    kwh_ph = kwh_p / punta_h if punta_h > 0 else 0.0
    kwh_lh = kwh_l / llano_h if llano_h > 0 else 0.0
    kwh_vh = kwh_v / valle_h if valle_h > 0 else 0.0

    pvpc_energy = 0.0
    missing_prices = 0
    total_hours = 0

    current = start
    while current < end:
        day_prices = hourly_prices.get(current, {})
        for hour in range(24):
            period = _get_period(current, hour)
            if period == "punta":
                kwh = kwh_ph
            elif period == "llano":
                kwh = kwh_lh
            else:
                kwh = kwh_vh

            price = day_prices.get(hour)
            if price is not None:
                pvpc_energy += kwh * price
            else:
                missing_prices += 1
            total_hours += 1
        current += timedelta(days=1)

    actual_energy = (
        factura.energia.importe_energia_punta_eur
        + factura.energia.importe_energia_llano_eur
        + factura.energia.importe_energia_valle_eur
    )

    savings = actual_energy - pvpc_energy
    annual = savings * 365 / dias

    # Build detail string
    if savings > 0:
        head = (
            f"Con tu mismo consumo distribuido uniformemente, bajo la "
            f"tarifa regulada PVPC habrías pagado **€{pvpc_energy:.2f}** "
            f"por la energía en lugar de **€{actual_energy:.2f}** "
            f"— un ahorro estimado de **€{savings:.2f}** este periodo "
            f"(~€{annual:.0f}/año)."
        )
    elif savings < 0:
        head = (
            f"En este periodo concreto, la tarifa PVPC habría salido "
            f"**€{abs(savings):.2f} más cara** (€{pvpc_energy:.2f} vs "
            f"€{actual_energy:.2f} reales). Tu tarifa fija te protegió "
            f"de la volatilidad del mercado mayorista. Valora si "
            f"prefieres la estabilidad de un precio fijo o asumir el "
            f"riesgo de precios variables a cambio de un ahorro potencial."
        )
    else:
        return None

    caveats = []
    caveats.append(
        "La simulación distribuye tu consumo total de cada periodo "
        "(punta/llano/valle) uniformemente entre todas las horas de "
        "ese periodo. Sin tus datos horarios reales (Datadis), el "
        "resultado es una aproximación."
    )
    if missing_prices > 0:
        caveats.append(
            f"Faltan precios PVPC para {missing_prices} hora(s) del "
            f"periodo — se trataron como 0 €/kWh, lo que puede "
            f"infravalorar el coste PVPC real."
        )
    if savings > 0:
        caveats.append(
            "Los impuestos (IE e IVA) también serían menores al "
            "reducirse la base imponible, así que el ahorro total "
            "sería ligeramente superior al estimado aquí."
        )

    detail = head + "\n\n" + "\n\n".join(caveats)

    return ComparisonResult(
        actual_energy_cost_eur=actual_energy,
        pvpc_energy_cost_eur=pvpc_energy,
        savings_energy_eur=savings,
        annual_savings_eur=annual,
        pvpc_is_cheaper=savings > 0,
        detail=detail,
    )
