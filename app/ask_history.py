"""Persist Ask Ledgerly Q&A history to the database."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from app.db import (
    insert_ask_history_complete,
    insert_ask_history_pending,
    list_ask_history,
    update_ask_history_result,
)
from app.models import AskHistoryItem, AskRequest


def doc_filter_from_request(ask_request: AskRequest) -> str | None:
    if ask_request.doc_id:
        return ask_request.doc_id
    if ask_request.tag:
        return f"tag:{ask_request.tag}"
    return None


def insert_pending_for_job(
    conn: Any,
    job_id: str,
    ask_request: AskRequest,
    asked_at: float | None = None,
) -> None:
    ts = int(asked_at if asked_at is not None else time.time())
    insert_ask_history_pending(
        conn,
        id=job_id,
        job_id=job_id,
        asked_at=ts,
        question=ask_request.question.strip(),
        doc_filter=doc_filter_from_request(ask_request),
    )


def insert_complete_answer(
    conn: Any,
    ask_request: AskRequest,
    answer: str,
    *,
    tables: list | None = None,
    charts: list | None = None,
    route: str | None = None,
    asked_at: float | None = None,
) -> None:
    ts = int(asked_at if asked_at is not None else time.time())
    tables_json = json.dumps(tables) if tables else None
    charts_json = json.dumps(charts) if charts else None
    insert_ask_history_complete(
        conn,
        id=uuid.uuid4().hex,
        asked_at=ts,
        question=ask_request.question.strip(),
        answer=answer,
        tables_json=tables_json,
        charts_json=charts_json,
        route=route,
        doc_filter=doc_filter_from_request(ask_request),
    )


def update_job_result(
    conn: Any,
    job_id: str,
    *,
    status: str,
    answer: str | None = None,
    tables: list | None = None,
    charts: list | None = None,
    route: str | None = None,
    error: str | None = None,
) -> None:
    tables_json = json.dumps(tables) if tables else None
    charts_json = json.dumps(charts) if charts else None
    update_ask_history_result(
        conn,
        job_id,
        status=status,
        answer=answer,
        tables_json=tables_json,
        charts_json=charts_json,
        route=route,
        error=error,
    )


def rows_to_history_items(rows: list[tuple]) -> list[AskHistoryItem]:
    items: list[AskHistoryItem] = []
    for row in rows:
        (
            id_,
            job_id,
            asked_at,
            status,
            question,
            answer,
            tables_json,
            charts_json,
            route,
            doc_filter,
            error,
        ) = row
        tables = json.loads(tables_json) if tables_json else []
        charts = json.loads(charts_json) if charts_json else []
        items.append(
            AskHistoryItem(
                id=id_,
                job_id=job_id,
                asked_at=int(asked_at),
                status=status,
                question=question,
                answer=answer,
                tables=tables,
                charts=charts,
                route=route,
                doc_filter=doc_filter,
                error=error,
            )
        )
    return items


def fetch_ask_history(conn: Any, limit: int = 50) -> list[AskHistoryItem]:
    return rows_to_history_items(list_ask_history(conn, limit=limit))
