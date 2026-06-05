"""Logger for the bill-advisor application.

Writes to both stdout (for docker logs) and a rotating file at
``/app/logs/bill-advisor.log`` (persists across container rebuilds).

Usage::

    from bill_advisor.logger import logger

    logger.info("Extrayendo datos con Claude...")
    logger.error("API call failed: %s", exc)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_LOG_DIR = Path("/app/logs")
_LOG_FILE = _LOG_DIR / "bill-advisor.log"
_FORMAT = "[Bill Advisor] %(message)s"

_logger = logging.getLogger("bill_advisor")
_logger.setLevel(logging.INFO)

# stdout handler — goes to docker logs
_stdout = logging.StreamHandler(sys.stdout)
_stdout.setFormatter(logging.Formatter(_FORMAT))
_logger.addHandler(_stdout)

# file handler — persists across container restarts
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_file = logging.FileHandler(str(_LOG_FILE), encoding="utf-8")
_file.setFormatter(logging.Formatter(_FORMAT))
_logger.addHandler(_file)


logger = _logger
