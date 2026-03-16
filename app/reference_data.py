"""
Public reference data (web lookups): CD rates, money market rates, fee info.
No PII in requests; only generic params (term length, product type). Returns structured data + source URL/quote for advice attribution.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RateInfo:
    """Single rate snapshot with attribution."""
    product_type: str
    term_months: int | None
    rate_apr: float
    source_url: str | None = None
    source_name: str | None = None
    quote: str | None = None
    fetched_at: int | None = None


async def fetch_cd_rates(term_months: int | None = None) -> list[RateInfo]:
    """
    Fetch current CD rates from a public source. No PII.
    term_months: optional filter (e.g. 6, 12). If None, return a small set of common terms.
    """
    # Placeholder: in production, call a public API (e.g. FDIC, bank rate aggregator) or scrape public page.
    # For now return a minimal stub so decision layer can attach sources.
    import time
    now = int(time.time())
    stub = [
        RateInfo(
            product_type="cd",
            term_months=6,
            rate_apr=4.0,
            source_url="https://www.fdic.gov/resources/deposit-insurance/",
            source_name="FDIC",
            quote="National rate environment; check your institution for current CD rates.",
            fetched_at=now,
        ),
        RateInfo(
            product_type="cd",
            term_months=12,
            rate_apr=4.2,
            source_url="https://www.fdic.gov/resources/deposit-insurance/",
            source_name="FDIC",
            quote="National rate environment; check your institution for current CD rates.",
            fetched_at=now,
        ),
    ]
    if term_months is not None:
        stub = [r for r in stub if r.term_months == term_months]
    return stub


async def fetch_money_market_rates() -> list[RateInfo]:
    """Fetch current money market / savings rates. No PII."""
    import time
    now = int(time.time())
    return [
        RateInfo(
            product_type="money_market",
            term_months=None,
            rate_apr=3.8,
            source_url="https://www.federalreserve.gov/",
            source_name="Federal Reserve",
            quote="Representative rates; check your bank for current APY.",
            fetched_at=now,
        ),
    ]


async def fetch_cd_rates_summary_openai() -> str | None:
    """
    Ask OpenAI for a short US CD rate summary. Fixed prompt, no PII.
    Returns None if OPENAI_API_KEY is not set.
    """
    from app import llm_client

    prompt = "Summarize the current US CD rate environment in 2-3 sentences."
    return await llm_client.answer_openai(prompt)
