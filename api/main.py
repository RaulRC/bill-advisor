"""FastAPI layer wrapping bill_advisor.extraction + bill_advisor.audit.

Designed to be consumed by the Next.js frontend. Endpoints:

- ``GET  /api/health``    — liveness probe.
- ``POST /api/analyze``   — multipart PDF upload → ``{factura, findings}``.

Dev run::

    uvicorn api.main:app --reload --port 8000
"""

import time
from dataclasses import asdict

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from api.rate_limiter import RateLimitMiddleware
from bill_advisor.audit import audit
from bill_advisor.extraction import extract_factura
from bill_advisor.logger import logger

load_dotenv()

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
    max_requests=10,
    window_seconds=60,
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
