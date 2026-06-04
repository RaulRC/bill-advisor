"""RAG-style Q&A about a Spanish electricity bill.

Loads corpus docs at module import. Each call to :func:`ask` sends the
corpus + the user's factura + the user's question to Claude and returns
a plain-Spanish answer.

Usage::

    from bill_advisor.rag.query import ask

    answer = ask("¿Qué significa peajes?", factura)
"""

from __future__ import annotations

import os
from pathlib import Path

import anthropic

_CORPUS_DIR = Path(__file__).parent / "corpus"


def _load_corpus() -> str:
    """Concatenate all markdown corpus files into one string."""
    parts: list[str] = []
    for path in sorted(_CORPUS_DIR.glob("*.md")):
        parts.append(path.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


_CORPUS_TEXT = _load_corpus()

_SYSTEM_PROMPT = f"""Eres un asesor energético experto en facturas eléctricas españolas.

Tu trabajo es responder preguntas de un usuario sobre su propia factura eléctrica.
Habla en español claro y directo. Usa los datos concretos de la factura del usuario
cuando sea relevante (importes, consumos, periodos). Si no sabes la respuesta, di que
no tienes esa información en lugar de inventar.

A continuación tienes documentación técnica sobre conceptos eléctricos. Úsala como
referencia para contextualizar tus respuestas:

--- DOCUMENTACIÓN DE REFERENCIA ---
{_CORPUS_TEXT}
--- FIN DOCUMENTACIÓN DE REFERENCIA ---

Siempre que menciones un importe concreto de la factura, ponlo en negritas con **.
Si das consejos, sé prudente — esto es orientativo, no vinculante."""


def ask(
    question: str,
    factura_json: dict,
    *,
    client: anthropic.Anthropic | None = None,
) -> str:
    """Answer a question about the user's electricity bill.

    Args:
        question: The user's question in Spanish.
        factura_json: Factura in JSON/dict form (from ``model_dump(mode="json")``).
        client: Optional Anthropic client. Creates a default one if None.

    Returns:
        The assistant's answer as plain text.
    """
    if client is None:
        client = anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"],
        )

    res = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            },
        ],
        messages=[
            {
                "role": "user",
                "content": (
                    "Aquí tienes mi factura en formato JSON:\n\n"
                    f"```json\n{factura_json}\n```\n\n"
                    f"Mi pregunta es: {question}"
                ),
            },
        ],
    )

    return res.content[0].text
