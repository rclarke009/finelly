"""Reference CD rate data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RateInfo:
    quote: str
    source_url: str | None = None
    source_name: str | None = None


async def fetch_cd_rates() -> list[RateInfo]:
    return []
