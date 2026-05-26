from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Contrato(BaseModel):
    """Datos de contrato. Tarifa de acceso casi siempre 2.0TD en doméstico."""

    cups: str = Field(description="Código CUPS, formato ES + 20 caracteres")
    direccion_suministro: Optional[str] = None
    comercializadora: str = Field(
        description="Quién factura (Iberdrola, Endesa, Naturgy, Octopus...)"
    )
    distribuidora: Optional[str] = Field(
        None,
        description=(
            "Quién mantiene la red (i-DE, e-distribución, UFD...) — "
            "distinta de la comercializadora, no se puede cambiar"
        ),
    )
    tarifa_acceso: Literal["2.0TD", "3.0TD", "6.1TD"] = "2.0TD"
    tarifa_comercial: str = Field(
        description="Nombre comercial del plan, p.ej. 'Plan Estable', 'Tempo Happy', 'Una Tarifa'"
    )
    modalidad: Literal["PVPC", "Libre fija", "Libre indexada"]


class PeriodoFacturacion(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    dias_facturados: int
    numero_factura: Optional[str] = None
    fecha_emision: Optional[date] = None


class Potencia(BaseModel):
    """Bajo 2.0TD: 2 periodos de potencia (punta P1 y valle P2)."""

    potencia_punta_kw: float
    potencia_valle_kw: float
    importe_potencia_punta_eur: float
    importe_potencia_valle_eur: float
    precio_potencia_punta_eur_kw_dia: Optional[float] = None
    precio_potencia_valle_eur_kw_dia: Optional[float] = None


class CostesPVPC(BaseModel):
    """Componentes específicos de facturas PVPC.

    Bajo PVPC, el coste energético se descompone en peajes T+D (que viven en
    Energia) MÁS estos componentes facturados aparte. En mercado libre estos
    costes están integrados en el precio €/kWh y este sub-bloque queda null."""

    coste_energia_mercado_mayorista_eur: float = Field(
        description="Pass-through del precio horario de OMIE para el periodo facturado"
    )
    margen_comercializacion_eur: float = Field(
        description="Margen comercialización fijo regulado (€/kW·año × días/365)"
    )


class Energia(BaseModel):
    """Bajo 2.0TD: 3 periodos de energía (punta, llano, valle).

    IMPORTANTE: bajo PVPC, los importe_energia_* contienen SOLO los peajes T+D
    regulados (~15-20% del coste real). El coste mayorista y el margen viven
    en costes_pvpc. En mercado libre los importe_energia_* contienen el coste
    total y costes_pvpc es null."""

    kwh_punta: float
    kwh_llano: float
    kwh_valle: float
    importe_energia_punta_eur: float
    importe_energia_llano_eur: float
    importe_energia_valle_eur: float
    precio_energia_punta_eur_kwh: Optional[float] = None
    precio_energia_llano_eur_kwh: Optional[float] = None
    precio_energia_valle_eur_kwh: Optional[float] = None
    costes_pvpc: Optional[CostesPVPC] = Field(
        None,
        description="Solo poblar si modalidad == 'PVPC'. Null en mercado libre.",
    )

    @property
    def kwh_total(self) -> float:
        return self.kwh_punta + self.kwh_llano + self.kwh_valle


class OtroServicio(BaseModel):
    concepto: str
    importe_eur: float


class OtrosConceptos(BaseModel):
    descuento_bono_social_eur: Optional[float] = Field(
        None,
        description="Descuento RECIBIDO por consumidores vulnerables (valor positivo)",
    )
    coste_financiacion_bono_social_eur: Optional[float] = Field(
        None,
        description="Recargo PAGADO por todos los consumidores para financiar el bono social",
    )
    alquiler_equipos_medida_eur: Optional[float] = None
    excedentes_autoconsumo_eur: Optional[float] = Field(
        None, description="Negativo si es compensación al cliente"
    )
    otros_servicios: list[OtroServicio] = Field(
        default_factory=list,
        description="Mantenimiento, seguros, etc.",
    )


class Impuestos(BaseModel):
    importe_impuesto_electricidad_eur: float
    tipo_impuesto_electricidad_pct: Optional[float] = Field(
        None, description="Ha variado: 0.5%, 3.8%, 5.11%..."
    )
    importe_iva_eur: float
    tipo_iva_pct: float = Field(description="Ha variado entre 5%, 10% y 21%")


class Totales(BaseModel):
    subtotal_sin_impuestos_eur: float
    total_factura_eur: float


class ConceptoNoMapeado(BaseModel):
    """Línea de la factura que la extracción no supo clasificar.
    Crítico para que la auditoría no esconda cargos."""

    descripcion: str
    importe_eur: float


class Factura(BaseModel):
    contrato: Contrato
    periodo: PeriodoFacturacion
    potencia: Potencia
    energia: Energia
    otros: OtrosConceptos = Field(default_factory=OtrosConceptos)
    impuestos: Impuestos
    totales: Totales
    conceptos_no_mapeados: list[ConceptoNoMapeado] = Field(default_factory=list)
    notas_extraccion: list[str] = Field(
        default_factory=list,
        description="Avisos del extractor: campos inferidos, baja confianza, etc.",
    )
