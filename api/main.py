"""FastAPI layer wrapping bill_advisor.extraction + bill_advisor.audit.

Designed to be consumed by the Next.js frontend. Endpoints:

- ``GET  /api/health``    — liveness probe.
- ``POST /api/analyze``   — multipart PDF upload → ``{factura, findings}``.

Dev run::

    uvicorn api.main:app --reload --port 8000
"""

from dataclasses import asdict

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from bill_advisor.audit import audit
from bill_advisor.extraction import extract_factura

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


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze(pdf: UploadFile = File(...)) -> dict:
    if pdf.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(
            status_code=415,
            detail=f"Expected application/pdf, got {pdf.content_type}",
        )

    pdf_bytes = await pdf.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty PDF body")

    try:
        factura = extract_factura(pdf_bytes)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Extraction returned data that doesn't match the Factura schema: {exc}",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    findings = audit(factura)

    return {
        "factura": factura.model_dump(mode="json"),
        "findings": [asdict(f) for f in findings],
    }
