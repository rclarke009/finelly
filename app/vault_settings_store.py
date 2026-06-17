"""Vault settings store stub."""

from __future__ import annotations

from typing import Any


def effective_vault_root_source() -> str:
    return "env"


def file_settings_snapshot() -> dict[str, Any]:
    return {}


def resolve_vault_incoming_mode() -> str:
    from app.config import VAULT_INCOMING_MODE

    return VAULT_INCOMING_MODE


def resolve_vault_root() -> str | None:
    from app.config import LEDGERLY_ORIGINALS_VAULT

    return LEDGERLY_ORIGINALS_VAULT or None


def vault_root_is_from_env() -> bool:
    return True


def write_vault_settings_file(data: dict) -> None:
    return None
