"""
Structured lock timing logger for concurrency-critical paths.

Usage
-----
::

    from app.utils.lock_logger import lock_timer

    with lock_timer("enrollment", "Semester", semester_id, logger):
        row = db.query(Semester).filter(...).with_for_update().one()
        # ... read-modify-write ...

Emits one JSON log line at DEBUG level on entry (lock acquired) and one at
INFO level on exit (lock released), plus a summary INFO line with duration_ms.

Log schema (all fields always present)
--------------------------------------
``event``          one of ``lock_acquired`` | ``lock_released``
``pipeline``       string label, e.g. ``"enrollment"`` | ``"reward"`` | ``"skill"`` | ``"booking"``
``entity_type``    ORM model name, e.g. ``"Semester"`` | ``"UserLicense"``
``entity_id``      int or None (None when the id is not known before the query)
``lock_acquired_at`` ISO-8601 UTC timestamp (lock_acquired event only)
``lock_released_at`` ISO-8601 UTC timestamp (lock_released event only)
``duration_ms``    float — wall-clock milliseconds held under lock (lock_released event only)

Design decisions
----------------
- Uses ``time.perf_counter()`` for sub-millisecond precision.
- Wall-clock UTC timestamps via ``datetime.now(timezone.utc)``.
- Emits ``lock_acquired`` at DEBUG so it does not flood production logs.
- Emits ``lock_released`` at INFO so lock_metrics.py can grep for it.
- Thread-safe: each ``with`` block has its own local ``t0``.
- Zero external dependencies (stdlib only + project logger).
"""
from __future__ import annotations

import json
import time
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

__all__ = ["lock_timer"]


@contextmanager
def lock_timer(
    pipeline: str,
    entity_type: str,
    entity_id: Optional[int],
    logger: logging.Logger,
):
    """
    Context manager that emits structured JSON log lines around a
    ``SELECT … FOR UPDATE`` block.

    Parameters
    ----------
    pipeline:
        Short label identifying the concurrency pipeline.
        Use one of: ``enrollment``, ``booking``, ``reward``, ``skill``.
    entity_type:
        ORM class name of the locked row, e.g. ``"Semester"``.
    entity_id:
        Primary key of the locked row, or ``None`` when not known before
        the query (e.g. when locking by a composite filter).
    logger:
        ``logging.Logger`` instance from the calling module.
    """
    acquired_at = datetime.now(timezone.utc)
    t0 = time.perf_counter()

    logger.debug(
        json.dumps({
            "event":           "lock_acquired",
            "pipeline":        pipeline,
            "entity_type":     entity_type,
            "entity_id":       entity_id,
            "lock_acquired_at": acquired_at.isoformat(),
        })
    )

    try:
        yield
    finally:
        t1 = time.perf_counter()
        released_at = datetime.now(timezone.utc)
        duration_ms = round((t1 - t0) * 1000, 3)

        logger.info(
            json.dumps({
                "event":            "lock_released",
                "pipeline":         pipeline,
                "entity_type":      entity_type,
                "entity_id":        entity_id,
                "lock_released_at": released_at.isoformat(),
                "duration_ms":      duration_ms,
            })
        )
