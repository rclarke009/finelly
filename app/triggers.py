"""
Trigger engine (Layer 3): evaluate maturity and obligation due dates.
Deterministic from Layer 2 tables only; no LLM.
Output: list of active triggers (or none). Optionally persist to trigger_events.
"""

import sqlite3
import time
from datetime import datetime, timedelta, timezone

from app.db import upsert_trigger_event

# Default: trigger when maturity or obligation is within this many days
MATURITY_DAYS_AHEAD = 30
OBLIGATION_DAYS_AHEAD = 30


def _parse_date(s: str | None) -> datetime | None:
    if not s or not s.strip():
        return None
    s = s.strip()[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def evaluate_triggers(
    conn: sqlite3.Connection,
    maturity_days_ahead: int = MATURITY_DAYS_AHEAD,
    obligation_days_ahead: int = OBLIGATION_DAYS_AHEAD,
    persist: bool = True,
    now_ts: int | None = None,
) -> list[tuple]:
    """
    Evaluate triggers from positions (maturity) and obligations (due date).
    Returns list of (id, trigger_type, entity_type, entity_id, event_date, evaluated_at, status).
    If persist=True, writes to trigger_events and returns the same shape from DB.
    """
    now_ts = now_ts or int(time.time())
    now = datetime.now(timezone.utc)
    maturity_cutoff = now + timedelta(days=maturity_days_ahead)
    obligation_cutoff = now + timedelta(days=obligation_days_ahead)
    triggers = []

    # Positions: CD (or any) maturity within N days
    positions = conn.execute(
        "SELECT id, account_id, asset_type, description, principal, rate_apr, maturity_date FROM positions WHERE maturity_date IS NOT NULL AND maturity_date != ''"
    ).fetchall()
    for row in positions:
        pos_id, account_id, asset_type, desc, principal, rate_apr, maturity_date = row
        d = _parse_date(maturity_date)
        if d and now <= d <= maturity_cutoff:
            trigger_id = f"maturity:{pos_id}"
            event_date = maturity_date
            triggers.append(
                (trigger_id, "maturity", "position", pos_id, event_date, now_ts, "pending")
            )

    # Obligations: due within N days
    obligations = conn.execute(
        "SELECT id, description, due_date, amount_estimate, priority FROM obligations"
    ).fetchall()
    for row in obligations:
        obl_id, desc, due_date, amount_estimate, priority = row
        d = _parse_date(due_date)
        if d and now <= d <= obligation_cutoff:
            trigger_id = f"obligation_due:{obl_id}"
            triggers.append(
                (trigger_id, "obligation_due", "obligation", obl_id, due_date, now_ts, "pending")
            )

    if persist:
        for t in triggers:
            trigger_id, trigger_type, entity_type, entity_id, event_date, evaluated_at, status = t
            upsert_trigger_event(
                conn, trigger_id, trigger_type, entity_type, entity_id, evaluated_at, status, event_date
            )
        conn.commit()

    return triggers


def get_active_triggers(
    conn: sqlite3.Connection,
    status: str = "pending",
    limit: int = 50,
) -> list[tuple]:
    """Return trigger_events rows (id, trigger_type, entity_type, entity_id, event_date, evaluated_at, status) with status=pending by default."""
    cursor = conn.execute(
        "SELECT id, trigger_type, entity_type, entity_id, event_date, evaluated_at, status FROM trigger_events WHERE status = ? ORDER BY evaluated_at DESC LIMIT ?",
        (status, limit),
    )
    return cursor.fetchall()
