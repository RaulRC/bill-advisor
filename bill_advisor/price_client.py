from __future__ import annotations

import os
from datetime import date, datetime

import httpx

from bill_advisor._cache import ttl_cache

ESIOS_INDICATOR_OMIE = 600
GEO_ESPAÑA = 3
BASE_URL = "https://api.esios.ree.es"


@ttl_cache(3600)
def fetch_omie_prices(
    start_date: date,
    end_date: date,
    *,
    esios_token: str | None = None,
) -> dict[date, dict[int, float]]:
    """Fetch hourly day-ahead (OMIE) market prices (€/MWh) for a date range.

    Returns {date: {hour (0-23): price_eur_per_mwh}} for Península.
    """
    if esios_token is None:
        esios_token = os.environ.get("ESIOS_TOKEN")
    if not esios_token:
        raise RuntimeError(
            "ESIOS_TOKEN not configured. "
            "Set ESIOS_TOKEN in .env or pass esios_token."
        )

    url = f"{BASE_URL}/indicators/{ESIOS_INDICATOR_OMIE}"
    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "time_trunc": "hour",
    }
    headers = {"x-api-key": esios_token, "Accept": "application/json"}

    with httpx.Client() as client:
        resp = client.get(url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

    values = data.get("indicator", {}).get("values", [])
    result: dict[date, dict[int, float]] = {}
    for entry in values:
        if entry.get("geo_id") != GEO_ESPAÑA:
            continue
        dt = datetime.fromisoformat(entry["datetime"])
        d = dt.date()
        hour = dt.hour
        result.setdefault(d, {})[hour] = entry["value"]

    return result
