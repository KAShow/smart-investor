"""Cryptographically secure token generation."""
import secrets


def generate_share_token() -> str:
    """256-bit URL-safe token for analysis share links."""
    return secrets.token_urlsafe(32)


def generate_pending_token() -> str:
    """128-bit URL-safe token for short-lived pending-analysis handoff."""
    return secrets.token_urlsafe(16)
