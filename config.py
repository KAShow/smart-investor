"""Centralized configuration loaded from environment variables."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
ENV_PATH = ROOT_DIR / '.env'
load_dotenv(ENV_PATH)


class Config:
    PROJECT_ROOT = ROOT_DIR
    DB_PATH = ROOT_DIR / "analyses.db"

    # Flask
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    PORT = int(os.getenv('PORT', 5000))
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', os.urandom(32).hex())

    # CORS — origins allowed to call the API
    CORS_ORIGINS = [
        o.strip()
        for o in os.getenv(
            'CORS_ORIGINS',
            'https://hawsh-khalifa.lovable.app,http://localhost:5173,http://localhost:8080,http://localhost:3000'
        ).split(',')
        if o.strip()
    ]

    # Supabase JWT — supports multiple trusted issuers (one per Supabase project)
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_JWT_SECRET = os.getenv('SUPABASE_JWT_SECRET', '')
    SUPABASE_JWT_AUDIENCE = os.getenv('SUPABASE_JWT_AUDIENCE', 'authenticated')
    # Comma-separated list of Supabase project base URLs (e.g. https://abc.supabase.co).
    # Each project's /auth/v1/.well-known/jwks.json is trusted.
    # Falls back to [SUPABASE_URL] if unset, for backward compatibility.
    SUPABASE_TRUSTED_PROJECTS = [
        u.strip().rstrip('/')
        for u in os.getenv('SUPABASE_TRUSTED_PROJECTS', os.getenv('SUPABASE_URL', '')).split(',')
        if u.strip()
    ]

    # Encryption for PII at rest
    FERNET_KEY = os.getenv('FERNET_KEY', '')

    # Perplexity (single shared key — owner pays)
    PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY', '')
    PERPLEXITY_DEFAULT_MODEL = os.getenv('PERPLEXITY_DEFAULT_MODEL', 'sonar-pro')

    # Other AI providers (kept for fallback)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

    # Rate limiting (Redis backed)
    REDIS_URL = os.getenv('REDIS_URL', 'memory://')
    RATE_LIMIT_PER_USER_DAY = os.getenv('RATE_LIMIT_PER_USER_DAY', '5/day')
    RATE_LIMIT_PER_IP_MINUTE = os.getenv('RATE_LIMIT_PER_IP_MINUTE', '30/minute')

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

    # Admin (for /api/admin/* endpoints)
    ADMIN_USER_IDS = [
        u.strip() for u in os.getenv('ADMIN_USER_IDS', '').split(',') if u.strip()
    ]

    # Token / share link expiry
    SHARE_TOKEN_EXPIRY_DAYS = int(os.getenv('SHARE_TOKEN_EXPIRY_DAYS', 180))

    # Pending analysis token TTL (seconds)
    PENDING_TTL_SECONDS = int(os.getenv('PENDING_TTL_SECONDS', 600))

    # SSE timeout (seconds before giving up on agents)
    SSE_TIMEOUT_SECONDS = int(os.getenv('SSE_TIMEOUT_SECONDS', 300))


def is_admin(user_id: str) -> bool:
    return bool(user_id) and user_id in Config.ADMIN_USER_IDS
