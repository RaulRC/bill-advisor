"""Streamlit UI for the bill advisor.

Run with: streamlit run app.py

Phase 1: upload PDF → show key facts + audit findings + extracted detail.
No Datadis, no comparator yet.
"""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

from bill_advisor.audit import Finding, audit
from bill_advisor.extraction import extract_factura
from bill_advisor.rag.query import ask
from bill_advisor.schemas import Factura

load_dotenv()


@st.cache_data(show_spinner=False)
def _extract_cached(pdf_bytes: bytes) -> Factura:
    """Re-uploading the same PDF in one session won't re-bill the API."""
    return extract_factura(pdf_bytes)


def main() -> None:
    st.set_page_config(
        page_title="Bill Advisor",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.title("Bill Advisor")
    st.caption(
        "Sube tu factura eléctrica española en PDF y obtén un análisis "
        "automático de cargos, anomalías y oportunidades de ahorro."
    )

    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error(
            "Falta `ANTHROPIC_API_KEY` en el entorno. "
            "Configúrala en un archivo `.env` en la raíz del proyecto."
        )
        st.stop()

    uploaded = st.file_uploader(
        "Arrastra tu factura PDF aquí",
        type=["pdf"],
        accept_multiple_files=False,
    )
    if uploaded is None:
        st.info("Esperando una factura PDF para analizar...")
        return

    pdf_bytes = uploaded.getvalue()

    try:
        with st.status("Extrayendo datos con Claude...") as status:
            print("[Bill Advisor] Extrayendo datos con Claude...")
            factura = _extract_cached(pdf_bytes)
            print(
                f"[Bill Advisor]  → extraída: {factura.contrato.modalidad}, "
                f"{factura.contrato.comercializadora}, "
                f"{factura.periodo.fecha_inicio.strftime('%d/%m/%Y')} → "
                f"{factura.periodo.fecha_fin.strftime('%d/%m/%Y')}, "
                f"{factura.energia.kwh_total:.0f} kWh, "
                f"€{factura.totales.total_factura_eur:.2f}"
            )
            status.update(label="Factura extraída correctamente", state="complete")

            status.update(
                label="Ejecutando auditoría (10 checks)...", state="running"
            )
            print("[Bill Advisor] Ejecutando auditoría (10 checks)...")
            findings = audit(factura)

            pvpc_findings = [
                f for f in findings if f.code == "pvpc_comparison"
            ]
            if pvpc_findings:
                f_pvpc = pvpc_findings[0]
                print(f"[Bill Advisor]  → PVPC: {f_pvpc.titulo}")
                if f_pvpc.ahorro_estimado_eur_mes:
                    annual = f_pvpc.ahorro_estimado_eur_mes * 12
                    print(f"[Bill Advisor]     ahorro estimado: ~€{annual:.0f}/año")
            else:
                print(
                    "[Bill Advisor]  → PVPC: no aplica "
                    "(PVPC bill o ESIOS no disponible)"
                )
            print(f"[Bill Advisor]  → {len(findings)} hallazgos encontrados")
            status.update(
                label=f"Auditoría completada ({len(findings)} hallazgos)",
                state="complete",
            )

            status.update(label="Renderizando resultados...", state="running")
            print("[Bill Advisor] Renderizando resultados en UI...")

    except Exception as exc:  # noqa: BLE001 - surface everything to the user
        st.error(
            f"Error al analizar la factura.\n\n"
            f"**{type(exc).__name__}**: {exc}"
        )
        st.caption(
            "Verifica que el PDF sea una factura eléctrica española válida "
            "y que tu API key sea correcta."
        )
        print(f"[Bill Advisor] ERROR: {type(exc).__name__}: {exc}")
        return

    _render_summary(factura)
    _render_findings(findings)
    _render_detalle(factura)
    _render_notas(factura)
    _render_chat(factura)


# -- Sections ---------------------------------------------------------------


def _render_summary(f: Factura) -> None:
    st.divider()
    st.subheader("Resumen")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total factura", f"€{f.totales.total_factura_eur:.2f}")
    col2.metric("Consumo", f"{f.energia.kwh_total:.0f} kWh")
    if f.energia.kwh_total > 0:
        col3.metric(
            "Precio efectivo",
            f"€{f.totales.total_factura_eur / f.energia.kwh_total:.4f}/kWh",
            help="Total factura ÷ consumo total. Incluye potencia, energía, impuestos.",
        )
    col4.metric("Días facturados", f.periodo.dias_facturados)

    st.markdown("&nbsp;")  # spacer

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("**Comercializadora**")
        st.write(f.contrato.comercializadora)
        st.markdown("**Distribuidora**")
        st.write(f.contrato.distribuidora or "_(no detectada)_")
        st.markdown("**Modalidad**")
        st.write(f"{f.contrato.modalidad}  ·  Tarifa {f.contrato.tarifa_acceso}")
    with col_right:
        st.markdown("**Tarifa comercial**")
        st.write(f.contrato.tarifa_comercial)
        st.markdown("**Periodo facturado**")
        st.write(
            f"{f.periodo.fecha_inicio.strftime('%d/%m/%Y')} → "
            f"{f.periodo.fecha_fin.strftime('%d/%m/%Y')}"
        )
        st.markdown("**CUPS**")
        st.code(f.contrato.cups, language=None)


def _render_findings(findings: list[Finding]) -> None:
    st.divider()
    st.subheader("Hallazgos")

    # The notas-from-extractor findings are shown in their own dedicated section
    # below; filter them out here to avoid double-rendering.
    visible = [f for f in findings if f.code != "nota_extractor"]

    criticals = [f for f in visible if f.severity == "critical"]
    warnings = [f for f in visible if f.severity == "warning"]
    infos = [f for f in visible if f.severity == "info"]

    if not visible:
        st.success("No se detectaron problemas en la factura.")
        return

    for finding in criticals:
        _render_finding_card(finding, st.error)
    for finding in warnings:
        _render_finding_card(finding, st.warning)

    if infos:
        with st.expander(f"Información adicional ({len(infos)})", expanded=False):
            for finding in infos:
                _render_finding_card(finding, st.info)


def _render_finding_card(finding: Finding, level_widget) -> None:
    head = finding.titulo
    if finding.ahorro_estimado_eur_mes:
        annual = finding.ahorro_estimado_eur_mes * 12
        head += f"  —  ahorro estimado ~€{annual:.2f}/año"
    level_widget(head)
    st.caption(finding.detalle)


def _render_detalle(f: Factura) -> None:
    st.divider()
    with st.expander("Detalle completo de la factura", expanded=False):
        st.markdown("##### Potencia")
        st.dataframe(
            _potencia_rows(f), use_container_width=True, hide_index=True
        )

        st.markdown("##### Energía (peajes T+D)")
        st.dataframe(
            _energia_rows(f), use_container_width=True, hide_index=True
        )

        if f.energia.costes_pvpc:
            st.markdown("##### Componentes PVPC adicionales")
            st.dataframe(
                [
                    {
                        "Concepto": "Coste energía mercado mayorista (OMIE)",
                        "Importe (€)": f.energia.costes_pvpc.coste_energia_mercado_mayorista_eur,
                    },
                    {
                        "Concepto": "Margen comercialización fijo",
                        "Importe (€)": f.energia.costes_pvpc.margen_comercializacion_eur,
                    },
                ],
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("##### Otros conceptos")
        st.dataframe(_otros_rows(f), use_container_width=True, hide_index=True)

        st.markdown("##### Impuestos y totales")
        st.dataframe(_impuestos_rows(f), use_container_width=True, hide_index=True)


def _potencia_rows(f: Factura) -> list[dict]:
    p = f.potencia
    return [
        {
            "Periodo": "Punta (P1)",
            "Potencia (kW)": p.potencia_punta_kw,
            "Precio (€/kW·día)": p.precio_potencia_punta_eur_kw_dia,
            "Importe (€)": p.importe_potencia_punta_eur,
        },
        {
            "Periodo": "Valle (P2)",
            "Potencia (kW)": p.potencia_valle_kw,
            "Precio (€/kW·día)": p.precio_potencia_valle_eur_kw_dia,
            "Importe (€)": p.importe_potencia_valle_eur,
        },
    ]


def _energia_rows(f: Factura) -> list[dict]:
    e = f.energia
    return [
        {
            "Periodo": "Punta (P1)",
            "Consumo (kWh)": e.kwh_punta,
            "Precio (€/kWh)": e.precio_energia_punta_eur_kwh,
            "Importe (€)": e.importe_energia_punta_eur,
        },
        {
            "Periodo": "Llano (P2)",
            "Consumo (kWh)": e.kwh_llano,
            "Precio (€/kWh)": e.precio_energia_llano_eur_kwh,
            "Importe (€)": e.importe_energia_llano_eur,
        },
        {
            "Periodo": "Valle (P3)",
            "Consumo (kWh)": e.kwh_valle,
            "Precio (€/kWh)": e.precio_energia_valle_eur_kwh,
            "Importe (€)": e.importe_energia_valle_eur,
        },
    ]


def _otros_rows(f: Factura) -> list[dict]:
    rows = []
    o = f.otros
    if o.descuento_bono_social_eur:
        rows.append(
            {"Concepto": "Descuento bono social", "Importe (€)": -o.descuento_bono_social_eur}
        )
    if o.coste_financiacion_bono_social_eur:
        rows.append(
            {
                "Concepto": "Financiación bono social",
                "Importe (€)": o.coste_financiacion_bono_social_eur,
            }
        )
    if o.alquiler_equipos_medida_eur:
        rows.append(
            {"Concepto": "Alquiler equipos medida", "Importe (€)": o.alquiler_equipos_medida_eur}
        )
    if o.excedentes_autoconsumo_eur:
        rows.append(
            {"Concepto": "Excedentes autoconsumo", "Importe (€)": o.excedentes_autoconsumo_eur}
        )
    for serv in o.otros_servicios:
        rows.append({"Concepto": serv.concepto, "Importe (€)": serv.importe_eur})
    if not rows:
        rows.append({"Concepto": "(sin otros conceptos)", "Importe (€)": 0.0})
    return rows


def _impuestos_rows(f: Factura) -> list[dict]:
    rows = [
        {
            "Concepto": "Subtotal sin impuestos",
            "Tipo / Detalle": "—",
            "Importe (€)": f.totales.subtotal_sin_impuestos_eur,
        },
        {
            "Concepto": "Impuesto sobre la electricidad",
            "Tipo / Detalle": (
                f"{f.impuestos.tipo_impuesto_electricidad_pct}%"
                if f.impuestos.tipo_impuesto_electricidad_pct is not None
                else "Mínimo unitario €/kWh"
            ),
            "Importe (€)": f.impuestos.importe_impuesto_electricidad_eur,
        },
        {
            "Concepto": "IVA",
            "Tipo / Detalle": f"{f.impuestos.tipo_iva_pct}%",
            "Importe (€)": f.impuestos.importe_iva_eur,
        },
        {
            "Concepto": "TOTAL FACTURA",
            "Tipo / Detalle": "—",
            "Importe (€)": f.totales.total_factura_eur,
        },
    ]
    return rows


def _render_notas(f: Factura) -> None:
    if not f.notas_extraccion:
        return
    st.divider()
    with st.expander(
        f"Notas del extractor ({len(f.notas_extraccion)})", expanded=False
    ):
        st.caption(
            "Observaciones automáticas del extractor sobre ambigüedades, "
            "inferencias o cosas que conviene revisar manualmente."
        )
        for i, nota in enumerate(f.notas_extraccion, 1):
            st.markdown(f"**{i}.** {nota}")


def _render_chat(f: Factura) -> None:
    """Chat interface for asking questions about the factura."""
    st.divider()
    st.subheader("💬 Pregunta sobre tu factura")
    st.caption(
        "Escribe una pregunta sobre cualquier concepto de tu factura. "
        "Ej: *¿Qué son los peajes?*, *¿Este cargo de €4,39 es normal?*, "
        "*¿Puedo ahorrar en potencia?*"
    )

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Escribe tu pregunta aquí..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"), st.spinner("Consultando documentación..."):
                print(f"[Bill Advisor] Chat: {prompt}")
                try:
                    answer = ask(
                        prompt,
                        f.model_dump(mode="json"),
                        messages=st.session_state.chat_messages,
                    )
                    st.markdown(answer)
                    st.session_state.chat_messages.append(
                        {"role": "assistant", "content": answer}
                    )
                    print("[Bill Advisor] Chat: respuesta enviada")
                except Exception as exc:  # noqa: BLE001
                    err = (
                        "Lo siento, no he podido responder. "
                        "Verifica que la API key de Anthropic esté configurada "
                        "y funcionando."
                    )
                    st.error(err)
                    print(f"[Bill Advisor] Chat ERROR: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
