"""Vault path validation stub."""

from __future__ import annotations


def validate_vault_root_path(path: str) -> tuple[bool, str | None]:
    if path and path.strip():
        return True, None
    return False, "Path required"
