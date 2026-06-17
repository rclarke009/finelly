"""Decision trigger evaluation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import MATURITY_DAYS_AHEAD, OBLIGATION_DAYS_AHEAD
from app.db import list_obligations, list_positions, upsert_trigger_event


def _parse_date(value: str | None) -> datetime | None:
    if not value or not str(value).strip():
        return None
    s = str(value).strip()[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def evaluate_triggers(
    conn: Any,
    *,
    maturity_days_ahead: int | None = None,
    obligation_days_ahead: int | None = None,
    persist: bool = False,
) -> list[tuple]:
    mat_days = maturity_days_ahead if maturity_days_ahead is not None else MATURITY_DAYS_AHEAD
    obl_days = obligation_days_ahead if obligation_days_ahead is not None else OBLIGATION_DAYS_AHEAD
    now = datetime.now(timezone.utc)
    mat_cutoff = now + timedelta(days=mat_days)
    obl_cutoff = now + timedelta(days=obl_days)
    evaluated_at = int(now.timestamp())
    triggers: list[tuple] = []

    for row in list_positions(conn):
        pos_id, _acc, _atype, _desc, _principal, _rate, maturity_date, *_rest = row
        d = _parse_date(maturity_date)
        if d is None:
            continue
        if now.date() <= d.date() <= mat_cutoff.date():
            tid = f"maturity:{pos_id}"
            triggers.append(
                (tid, "maturity", "position", pos_id, maturity_date, evaluated_at, "open")
            )
            if persist:
                upsert_trigger_event(
                    conn,
                    tid,
                    "maturity",
                    "position",
                    pos_id,
                    evaluated_at,
                    "open",
                    maturity_date,
                )

    for row in list_obligations(conn):
        obl_id, _desc, due_date, *_rest = row
        d = _parse_date(due_date)
        if d is None:
            continue
        if now.date() <= d.date() <= obl_cutoff.date():
            tid = f"obligation:{obl_id}"
            triggers.append(
                (tid, "obligation_due", "obligation", obl_id, due_date, evaluated_at, "open")
            )
            if persist:
                upsert_trigger_event(
                    conn,
                    tid,
                    "obligation_due",
                    "obligation",
                    obl_id,
                    evaluated_at,
                    "open",
                    due_date,
                )

    return triggers
