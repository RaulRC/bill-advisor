"""Prometheus metrics for the bill-advisor application.

Imported once at process start so metric registration only happens
once per interpreter session (avoids Streamlit re-execution errors).
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram, start_http_server

start_http_server(8001)

SESSIONS = Counter("bill_sessions", "Unique browser sessions")
EXTRACTIONS = Counter("bill_extractions", "Facturas extraídas")
ERRORS = Counter("bill_extraction_errors", "Extraction failures")
PVPC_SAVINGS_FOUND = Counter(
    "bill_pvpc_savings_found", "PVPC cheaper than current tariff"
)
PVPC_MORE_EXPENSIVE = Counter(
    "bill_pvpc_more_expensive", "Current tariff cheaper than PVPC"
)
CHAT_QUESTIONS = Counter("bill_chat_questions", "RAG chat questions asked")
EXTRACTION_DURATION = Histogram(
    "bill_extraction_duration_seconds",
    "Extraction + audit wall time",
    buckets=[5, 10, 20, 30, 45, 60, 90, 120],
)
