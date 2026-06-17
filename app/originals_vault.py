"""Originals vault stub."""

from __future__ import annotations


def vault_enabled() -> bool:
    from app.config import LEDGERLY_ORIGINALS_VAULT

    return bool(LEDGERLY_ORIGINALS_VAULT)


def vault_watcher_requested() -> bool:
    from app.config import VAULT_INCOMING_MODE

    return VAULT_INCOMING_MODE != "off"


def absolute_from_vault_relative(rel: str):
    return None
