"""FastAPI layer wrapping bill_advisor modules.

Endpoints:

- ``GET  /api/health``    — liveness probe.
- ``GET  /api/prices``    — today's & tomorrow's PVPC + OMIE prices.
- ``POST /api/chat``      — chat with RAG (general or invoice-aware).
- ``POST /api/analyze``   — multipart PDF upload → ``{factura, findings}``.
- ``GET  /<path>``        — serve frontend SPA (production).

Dev run::

    uvicorn api.main:app --reload --port 8000
"""

import time
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ValidationError

from api.rate_limiter import RateLimitMiddleware
from bill_advisor.audit import audit
from bill_advisor.extraction import extract_factura
from bill_advisor.logger import logger
from bill_advisor.price_client import fetch_omie_prices
from bill_advisor.pvpc_client import fetch_pvpc_prices
from bill_advisor.rag.query import ask, ask_general

load_dotenv()

_CHAT_MODEL = "claude-sonnet-4-6"
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"

app = FastAPI(
    title="Bill Advisor API",
    description="AI-powered auditor for Spanish residential electricity bills.",
    version="0.1.0",
)

# Next.js dev server runs on 3000; production origin will be added once deployed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.add_middleware(
    RateLimitMiddleware,
    max_requests=2,
    window_seconds=60,
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/prices")
def prices() -> dict:
    today = date.today()
    tomorrow = today + timedelta(days=1)

    def _series(data: dict[date, dict[int, float]], d: date, scale=1.0):
        return sorted(
            [{"hour": h, "price": round(v * scale, 4)} for h, v in data.get(d, {}).items()],
            key=lambda x: x["hour"],
        )

    try:
        pvpc = fetch_pvpc_prices(today, tomorrow)   # €/kWh
        omie = fetch_omie_prices(today, tomorrow)    # €/MWh
    except RuntimeError as exc:
        logger.warning("[API] GET /api/prices — %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))

    return {
        "pvpc": {
            "today": _series(pvpc, today, scale=1000),
            "tomorrow": _series(pvpc, tomorrow, scale=1000) or None,
        },
        "omie": {
            "today": _series(omie, today),
            "tomorrow": _series(omie, tomorrow) or None,
        },
        "currency": "EUR",
        "unit": "€/MWh",
    }


@app.post("/api/analyze")
async def analyze(pdf: UploadFile = File(...), request: Request = None) -> dict:
    client_ip = request.client.host if request and request.client else "unknown"
    pdf_bytes = await pdf.read()
    t0 = time.time()

    logger.info(
        "[API] POST /api/analyze — %d bytes, ip=%s", len(pdf_bytes), client_ip
    )

    if pdf.content_type not in {"application/pdf", "application/octet-stream"}:
        logger.info("[API]  → 415: content_type=%s", pdf.content_type)
        raise HTTPException(
            status_code=415,
            detail=f"Expected application/pdf, got {pdf.content_type}",
        )

    if not pdf_bytes:
        logger.info("[API]  → 400: empty body")
        raise HTTPException(status_code=400, detail="Empty PDF body")

    logger.info("[API] Extrayendo datos con Claude...")
    try:
        factura = extract_factura(pdf_bytes)
    except ValidationError as exc:
        logger.error("[API]  → 422: ValidationError: %s", exc)
        raise HTTPException(
            status_code=422,
            detail=f"Extraction returned data that doesn't match the Factura schema: {exc}",
        ) from exc
    except RuntimeError as exc:
        logger.error("[API]  → 502: RuntimeError: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    logger.info(
        "[API]  → extraída: %s, %s, %s → %s, %.0f kWh, €%.2f",
        factura.contrato.modalidad,
        factura.contrato.comercializadora,
        factura.periodo.fecha_inicio,
        factura.periodo.fecha_fin,
        factura.energia.kwh_total,
        factura.totales.total_factura_eur,
    )

    logger.info("[API] Ejecutando auditoría...")
    findings = audit(factura)

    pvpc_findings = [f for f in findings if f.code == "pvpc_comparison"]
    if pvpc_findings:
        f_pvpc = pvpc_findings[0]
        logger.info("[API]  → PVPC: %s", f_pvpc.titulo)
    else:
        logger.info("[API]  → PVPC: no aplica")
    logger.info("[API]  → %d hallazgos encontrados", len(findings))

    elapsed = time.time() - t0
    logger.info("[API]  → respuesta enviada (%.1fs)", elapsed)

    return {
        "factura": factura.model_dump(mode="json"),
        "findings": [asdict(f) for f in findings],
    }


class _ChatRequest(BaseModel):
    messages: list[dict]
    factura: dict | None = None
    prices: dict | None = None


def _price_summary(prices: dict) -> str | None:
    """Build a short Spanish summary from the prices payload."""
    pvpc_today = prices.get("pvpc", {}).get("today")
    omie_today = prices.get("omie", {}).get("today")
    if not pvpc_today or not omie_today:
        return None

    p_min = min(pvpc_today, key=lambda x: x["price"])
    p_max = max(pvpc_today, key=lambda x: x["price"])
    p_avg = sum(h["price"] for h in pvpc_today) / len(pvpc_today)
    o_min = min(omie_today, key=lambda x: x["price"])
    o_max = max(omie_today, key=lambda x: x["price"])
    o_avg = sum(h["price"] for h in omie_today) / len(omie_today)

    lines = [
        "Aquí tienes los precios de la electricidad para hoy (PVPC y OMIE en €/MWh):",
        "",
        f"- PVPC: mínimo {p_min['price']:.1f} €/MWh (h {p_min['hour']}:00), "
        f"máximo {p_max['price']:.1f} €/MWh (h {p_max['hour']}:00), "
        f"media {p_avg:.1f} €/MWh",
        f"- OMIE: mínimo {o_min['price']:.1f} €/MWh (h {o_min['hour']}:00), "
        f"máximo {o_max['price']:.1f} €/MWh (h {o_max['hour']}:00), "
        f"media {o_avg:.1f} €/MWh",
    ]

    tomorrow = prices.get("pvpc", {}).get("tomorrow")
    if tomorrow:
        t_min = min(tomorrow, key=lambda x: x["price"])
        t_max = max(tomorrow, key=lambda x: x["price"])
        lines.append(
            f"- Mañana (previsto PVPC): mínimo {t_min['price']:.1f} €/MWh, "
            f"máximo {t_max['price']:.1f} €/MWh"
        )

    lines.append("")
    lines.append("Los datos horarios completos están disponibles si el usuario pregunta por una hora concreta.")
    return "\n".join(lines)


@app.post("/api/chat")
def chat(body: _ChatRequest) -> dict:
    logger.info("[API] POST /api/chat — %d messages, factura=%s, prices=%s",
                len(body.messages),
                "yes" if body.factura else "no",
                "yes" if body.prices else "no")

    prices_context = _price_summary(body.prices) if body.prices else None

    if prices_context:
        messages = [
            {"role": "user", "content": prices_context},
            {"role": "assistant", "content": "Gracias, ya tengo los precios actuales. ¿Qué quieres saber?"},
            *body.messages,
        ]
    else:
        messages = body.messages

    if body.factura and prices_context:
        question = messages[-1]["content"]
        prev = messages[:-1]
        answer = ask(question, body.factura, messages=prev)
    elif body.factura:
        question = body.messages[-1]["content"]
        prev = body.messages[:-1]
        answer = ask(question, body.factura, messages=prev)
    else:
        answer = ask_general(messages)

    return {"answer": answer}


# ── Production: serve frontend SPA ──────────────────────────────────────────

@app.get("/{path:path}")
def _serve_frontend(path: str) -> FileResponse:
    index = _FRONTEND_DIR / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="Frontend not built")
    file = _FRONTEND_DIR / path
    if file.is_file():
        return FileResponse(file)
    return FileResponse(index)
