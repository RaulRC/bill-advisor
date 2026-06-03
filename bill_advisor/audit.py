"""Auditor for extracted Spanish electricity bills.

Pure logic — no LLM. Takes a validated :class:`Factura` and returns a list of
:class:`Finding` objects. Used by the UI to render warnings and by the
explainer (Phase 2) to drive recommendations.

Checks are deliberately conservative: false positives (flagging something
that's actually fine) erode trust faster than false negatives. Heuristics
that need hourly consumption data (Datadis) are deferred to Phase 2.

Note: ``_check_pvpc_comparison`` is the only check that makes an HTTP
call (to ESIOS). If the API is unreachable it silently returns ``[]`` so
the pipeline never breaks.
"""

import os
from dataclasses import dataclass
from typing import Literal

from bill_advisor.comparator import compare_with_pvpc
from bill_advisor.pvpc_client import fetch_pvpc_prices
from bill_advisor.schemas import Factura

Severity = Literal["info", "warning", "critical"]

VALID_IVA_PCTS: set[float] = {5.0, 10.0, 21.0}
BALANCE_TOLERANCE_EUR = 0.05


@dataclass(frozen=True)
class Finding:
    """A single audit observation.

    `ahorro_estimado_eur_mes` is populated only for findings tied to a
    quantifiable monthly cost the user could plausibly avoid. Don't fabricate
    estimates for uncertain savings — leave it None.
    """

    severity: Severity
    code: str
    titulo: str
    detalle: str
    ahorro_estimado_eur_mes: float | None = None


def _monthly_from_period(importe_eur: float, dias_facturados: int) -> float:
    """Annualise then divide by 12 — more accurate than ×30/days for short cycles."""
    if dias_facturados <= 0:
        return importe_eur
    return importe_eur * 365 / dias_facturados / 12


# -- Checks -----------------------------------------------------------------


def _check_effective_kwh_price(f: Factura) -> list[Finding]:
    """Always-emitted info: average €/kWh paid (after taxes)."""
    kwh = f.energia.kwh_total
    if kwh <= 0:
        return []
    eur_per_kwh = f.totales.total_factura_eur / kwh
    return [
        Finding(
            severity="info",
            code="precio_efectivo_kwh",
            titulo=f"Precio efectivo medio: €{eur_per_kwh:.4f}/kWh (con impuestos)",
            detalle=(
                f"Calculado como total factura (€{f.totales.total_factura_eur:.2f}) "
                f"dividido entre consumo total ({kwh:.0f} kWh). "
                f"Incluye potencia, energía, impuestos y todos los conceptos. "
                f"Útil para comparar entre facturas o tarifas."
            ),
        )
    ]


def _check_total_balance(f: Factura) -> list[Finding]:
    sum_potencia = (
        f.potencia.importe_potencia_punta_eur + f.potencia.importe_potencia_valle_eur
    )
    sum_energia_peajes = (
        f.energia.importe_energia_punta_eur
        + f.energia.importe_energia_llano_eur
        + f.energia.importe_energia_valle_eur
    )
    sum_pvpc = 0.0
    if f.energia.costes_pvpc:
        sum_pvpc = (
            f.energia.costes_pvpc.coste_energia_mercado_mayorista_eur
            + f.energia.costes_pvpc.margen_comercializacion_eur
        )
    sum_otros = (
        sum(s.importe_eur for s in f.otros.otros_servicios)
        + (f.otros.alquiler_equipos_medida_eur or 0)
        - (f.otros.descuento_bono_social_eur or 0)
        + (f.otros.coste_financiacion_bono_social_eur or 0)
        + (f.otros.excedentes_autoconsumo_eur or 0)
    )
    sum_no_mapeados = sum(c.importe_eur for c in f.conceptos_no_mapeados)

    computed_total = (
        sum_potencia
        + sum_energia_peajes
        + sum_pvpc
        + sum_otros
        + sum_no_mapeados
        + f.impuestos.importe_impuesto_electricidad_eur
        + f.impuestos.importe_iva_eur
    )
    delta = computed_total - f.totales.total_factura_eur

    if abs(delta) <= BALANCE_TOLERANCE_EUR:
        return []
    return [
        Finding(
            severity="critical",
            code="total_no_cuadra",
            titulo=f"El total facturado no cuadra (diferencia €{delta:+.2f})",
            detalle=(
                f"Suma de los conceptos extraídos: €{computed_total:.2f}. "
                f"Total declarado en la factura: €{f.totales.total_factura_eur:.2f}. "
                f"Esta discrepancia puede deberse a (a) un error de extracción "
                f"o (b) un cargo en la factura que la auditoría no contabilizó. "
                f"En cualquier caso, las recomendaciones de ahorro pueden ser "
                f"poco fiables hasta resolverlo."
            ),
        )
    ]


def _check_iva_pct_valid(f: Factura) -> list[Finding]:
    if f.impuestos.tipo_iva_pct in VALID_IVA_PCTS:
        return []
    return [
        Finding(
            severity="warning",
            code="iva_pct_inusual",
            titulo=f"Tipo IVA inusual: {f.impuestos.tipo_iva_pct}%",
            detalle=(
                f"Los tipos válidos de IVA eléctrico en España han sido 5%, 10% "
                f"y 21% según las medidas anti-crisis vigentes. Tu factura aplica "
                f"{f.impuestos.tipo_iva_pct}%, que no es un valor estándar. "
                f"Verifica con tu comercializadora si es correcto."
            ),
        )
    ]


def _check_iva_calculation(f: Factura) -> list[Finding]:
    base = (
        f.totales.subtotal_sin_impuestos_eur
        + f.impuestos.importe_impuesto_electricidad_eur
    )
    expected = base * f.impuestos.tipo_iva_pct / 100
    delta = expected - f.impuestos.importe_iva_eur
    if abs(delta) <= BALANCE_TOLERANCE_EUR:
        return []
    return [
        Finding(
            severity="warning",
            code="iva_calculo_no_cuadra",
            titulo=f"El IVA aplicado no coincide con el porcentaje declarado (diferencia €{delta:+.2f})",
            detalle=(
                f"Tipo declarado: {f.impuestos.tipo_iva_pct}%. "
                f"Base imponible (subtotal + impuesto eléctrico): €{base:.2f}. "
                f"IVA esperado: €{expected:.2f}. "
                f"IVA facturado: €{f.impuestos.importe_iva_eur:.2f}."
            ),
        )
    ]


def _check_alquiler_contador(f: Factura) -> list[Finding]:
    importe = f.otros.alquiler_equipos_medida_eur
    if not importe or importe <= 0:
        return []
    mensual = _monthly_from_period(importe, f.periodo.dias_facturados)
    return [
        Finding(
            severity="warning",
            code="alquiler_contador_presente",
            titulo=f"Pagas alquiler del contador (€{importe:.2f} este periodo)",
            detalle=(
                "Los contadores domésticos suelen amortizarse tras 12-15 años "
                "de servicio. Si tu contador es antiguo, podrías dejar de pagar "
                "el alquiler. Contacta a tu distribuidora (la entidad indicada "
                f"como '{f.contrato.distribuidora or 'distribuidora'}') para "
                "confirmar el estado de amortización del contador."
            ),
            ahorro_estimado_eur_mes=mensual,
        )
    ]


def _check_otros_servicios(f: Factura) -> list[Finding]:
    findings: list[Finding] = []
    for serv in f.otros.otros_servicios:
        mensual = _monthly_from_period(serv.importe_eur, f.periodo.dias_facturados)
        findings.append(
            Finding(
                severity="info",
                code="servicio_adicional",
                titulo=f"Servicio adicional: {serv.concepto} (€{serv.importe_eur:.2f})",
                detalle=(
                    "Producto añadido por la comercializadora (no regulado, "
                    "no obligatorio). Verifica si lo usas — la mayoría son "
                    "cancelables con una llamada o desde el área de cliente."
                ),
                ahorro_estimado_eur_mes=mensual,
            )
        )
    return findings


def _check_conceptos_no_mapeados(f: Factura) -> list[Finding]:
    if not f.conceptos_no_mapeados:
        return []
    total = sum(c.importe_eur for c in f.conceptos_no_mapeados)
    detalle_items = "; ".join(
        f"'{c.descripcion}' (€{c.importe_eur:.2f})" for c in f.conceptos_no_mapeados
    )
    return [
        Finding(
            severity="warning",
            code="conceptos_sin_clasificar",
            titulo=f"{len(f.conceptos_no_mapeados)} cargo(s) sin clasificar (€{total:.2f})",
            detalle=(
                f"El extractor no supo dónde encajar estos conceptos en el "
                f"esquema: {detalle_items}. Revisa manualmente — pueden ser "
                f"cargos legítimos no contemplados aún en el auditor."
            ),
        )
    ]


def _check_excedentes_solares(f: Factura) -> list[Finding]:
    excedentes = f.otros.excedentes_autoconsumo_eur
    if excedentes is None or excedentes >= 0:
        return []
    return [
        Finding(
            severity="info",
            code="autoconsumo_solar_excedentes",
            titulo=f"Autoconsumo solar con excedentes (compensación €{abs(excedentes):.2f})",
            detalle=(
                "Tienes instalación solar con vertido de excedentes a la red. "
                "La compensación por excedentes suele ser baja (~€0,003-0,06/kWh "
                "según hora). Para maximizar el ahorro, programa cargas flexibles "
                "(lavadora, lavavajillas, termo, vehículo eléctrico) en las "
                "horas de máxima generación solar — autoconsumir directamente "
                "ahorra el precio de venta (~€0,15/kWh) en lugar del precio "
                "de compensación. Phase 2 cuantificará esto con datos horarios."
            ),
        )
    ]


def _check_pvpc_comparison(f: Factura) -> list[Finding]:
    """Compare energy cost against PVPC for non-PVPC bills."""
    if f.contrato.modalidad == "PVPC":
        return []
    if not os.environ.get("ESIOS_TOKEN"):
        return []

    try:
        prices = fetch_pvpc_prices(
            f.periodo.fecha_inicio, f.periodo.fecha_fin
        )
    except Exception:
        return []

    result = compare_with_pvpc(f, prices)
    if result is None:
        return []

    if result.pvpc_is_cheaper:
        severity: Severity = (
            "warning" if result.annual_savings_eur >= 100 else "info"
        )
        titulo = (
            f"Ahorro estimado de ~€{result.annual_savings_eur:.0f}/año "
            f"cambiándote a PVPC"
        )
    else:
        severity = "info"
        titulo = (
            f"Con PVPC habrías pagado ~€{abs(result.savings_energy_eur):.2f} "
            f"más este periodo"
        )

    return [
        Finding(
            severity=severity,
            code="pvpc_comparison",
            titulo=titulo,
            detalle=result.detail,
            ahorro_estimado_eur_mes=(
                result.annual_savings_eur / 12
                if result.pvpc_is_cheaper else None
            ),
        )
    ]


def _check_notas_extraccion(f: Factura) -> list[Finding]:
    return [
        Finding(
            severity="info",
            code="nota_extractor",
            titulo="Nota del extractor (revisar)",
            detalle=nota,
        )
        for nota in f.notas_extraccion
    ]


# -- Public API -------------------------------------------------------------


_CHECKS = [
    _check_effective_kwh_price,
    _check_total_balance,
    _check_iva_pct_valid,
    _check_iva_calculation,
    _check_alquiler_contador,
    _check_otros_servicios,
    _check_conceptos_no_mapeados,
    _check_excedentes_solares,
    _check_pvpc_comparison,
    _check_notas_extraccion,
]

_SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def audit(factura: Factura) -> list[Finding]:
    """Run all checks. Returns findings sorted critical → warning → info."""
    findings: list[Finding] = []
    for check in _CHECKS:
        findings.extend(check(factura))
    return sorted(findings, key=lambda f: _SEVERITY_ORDER[f.severity])


# -- CLI --------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    from dotenv import load_dotenv

    from bill_advisor.extraction import extract_factura

    load_dotenv()

    if len(sys.argv) != 2:
        print(
            "Usage: python -m bill_advisor.audit <path-to-factura.pdf>",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(sys.argv[1], "rb") as fh:
        factura = extract_factura(fh.read())

    findings = audit(factura)
    markers = {"critical": "[!!!]", "warning": "[ ! ]", "info": "[ i ]"}

    print(f"\n=== AUDITORÍA: {len(findings)} hallazgo(s) ===\n")
    for finding in findings:
        marker = markers[finding.severity]
        head = f"{marker} {finding.titulo}"
        if finding.ahorro_estimado_eur_mes:
            head += f"  (~€{finding.ahorro_estimado_eur_mes:.2f}/mes)"
        print(head)
        print(f"        {finding.detalle}\n")
