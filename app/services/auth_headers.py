"""Compatibility module for user resolution (re-exports auth.resolve_user)."""
from services.auth import resolve_user

__all__ = ["resolve_user"]
