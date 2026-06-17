"""Answer markdown layout and structured JSON tail parsing."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field


class AnswerTable(BaseModel):
    title: str | None = None
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)


class AnswerChart(BaseModel):
    title: str | None = None
    chart_type: str = "bar"
    labels: list[str] = Field(default_factory=list)
    values: list[float] = Field(default_factory=list)

FINELLY_STRUCTURED_MARKER = "\n---FINELLY_STRUCTURED---\n"
ANSWER_FORMAT_PROMPT_SUFFIX = (
    "\n\nAfter your answer, on its own line, output exactly:\n"
    "---FINELLY_STRUCTURED---\n"
    "Then optional JSON with keys tables (array) and charts (array). "
    "Omit the marker if you have no structured data."
)


def split_structured(raw: str) -> tuple[str, dict[str, Any] | None]:
    if not raw:
        return "", None
    text = raw.replace("\r\n", "\n")
    idx = text.rfind(FINELLY_STRUCTURED_MARKER)
    if idx == -1:
        return raw.strip(), None
    body = text[:idx].strip()
    tail_raw = text[idx + len(FINELLY_STRUCTURED_MARKER) :].strip()
    if not tail_raw:
        return body, None
    try:
        tail = json.loads(tail_raw)
        if isinstance(tail, dict):
            return body, tail
    except json.JSONDecodeError:
        pass
    return body, None


def merge_structured_to_response(
    body: str,
    tail: dict[str, Any] | None,
) -> tuple[str, list[AnswerTable], list[AnswerChart]]:
    tables: list[AnswerTable] = []
    charts: list[AnswerChart] = []
    if tail:
        for t in tail.get("tables") or []:
            if isinstance(t, dict):
                try:
                    tables.append(AnswerTable.model_validate(t))
                except Exception:
                    pass
        for c in tail.get("charts") or []:
            if isinstance(c, dict):
                try:
                    charts.append(AnswerChart.model_validate(c))
                except Exception:
                    pass
    return body, tables, charts


def normalize_markdown_layout(md: str) -> str:
    if not md or not md.strip():
        return md or ""
    text = md.replace("\r\n", "\n")
    text = re.sub(r"(?<!\n)\s+(#{2,6}\s+)", r"\n\n\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
