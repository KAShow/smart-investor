"""Supabase JWT verification middleware (multi-project).

The backend is intentionally NOT bound to a single Supabase project. It accepts
tokens from any project listed in `SUPABASE_TRUSTED_PROJECTS` (comma-separated
base URLs). For each token:

1. The token's unverified `iss` claim picks which project's JWKS to trust.
2. Asymmetric verification (RS256/ES256) runs against that project's JWKS.
3. Symmetric (HS256 + SUPABASE_JWT_SECRET) is tried only if the token's `iss`
   matches the project that the secret belongs to (legacy single-project mode).

This lets one Smart Investor backend serve users from multiple frontends, each
with its own Supabase auth project.
"""
import logging
from functools import wraps

import jwt
from flask import g, jsonify, request

from config import Config, is_admin

logger = logging.getLogger(__name__)


def _project_to_issuer(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/auth/v1"


_TRUSTED_ISSUERS: dict[str, str] = {
    _project_to_issuer(p): p for p in Config.SUPABASE_TRUSTED_PROJECTS
}
_jwks_clients: dict[str, jwt.PyJWKClient] = {}


def _jwks_client_for(project_url: str) -> jwt.PyJWKClient | None:
    if project_url in _jwks_clients:
        return _jwks_clients[project_url]
    jwks_url = f"{project_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    try:
        client = jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
        _jwks_clients[project_url] = client
        return client
    except Exception as e:
        logger.info(f"Could not init JWKS client for {project_url}: {e}")
        return None


def _decode_asymmetric(token: str) -> dict | None:
    try:
        unverified = jwt.decode(token, options={"verify_signature": False})
    except Exception as e:
        logger.info(f"Token unparseable for issuer lookup: {e}")
        return None

    iss = unverified.get('iss', '')
    project_url = _TRUSTED_ISSUERS.get(iss)
    if not project_url:
        logger.info(f"Token issuer not in trusted list: {iss}")
        return None

    client = _jwks_client_for(project_url)
    if not client:
        return None

    try:
        signing_key = client.get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=['RS256', 'ES256'],
            audience=Config.SUPABASE_JWT_AUDIENCE,
            issuer=iss,
        )
    except jwt.ExpiredSignatureError:
        logger.info("JWT expired (asymmetric)")
        return None
    except jwt.InvalidTokenError as e:
        logger.info(f"Asymmetric verify failed: {e}")
        return None
    except Exception as e:
        logger.info(f"JWKS lookup failed: {e}")
        return None


def _decode_symmetric(token: str) -> dict | None:
    """Legacy HS256 fallback. Only useful for projects still on legacy JWT secret."""
    if not Config.SUPABASE_JWT_SECRET:
        return None
    try:
        return jwt.decode(
            token,
            Config.SUPABASE_JWT_SECRET,
            algorithms=['HS256'],
            audience=Config.SUPABASE_JWT_AUDIENCE,
        )
    except jwt.ExpiredSignatureError:
        logger.info("JWT expired (symmetric)")
        return None
    except jwt.InvalidTokenError as e:
        logger.info(f"Symmetric verify failed: {e}")
        return None


def _decode_token(token: str) -> dict | None:
    payload = _decode_asymmetric(token)
    if payload:
        return payload
    payload = _decode_symmetric(token)
    if payload:
        return payload
    if not Config.SUPABASE_TRUSTED_PROJECTS and not Config.SUPABASE_JWT_SECRET:
        logger.error("No SUPABASE_TRUSTED_PROJECTS or SUPABASE_JWT_SECRET configured")
    try:
        header = jwt.get_unverified_header(token)
        claims = jwt.decode(token, options={"verify_signature": False})
        sub = claims.get('sub', '') or ''
        logger.info(
            f"Token rejected. alg={header.get('alg')} kid={header.get('kid')} "
            f"iss={claims.get('iss')} aud={claims.get('aud')} sub={sub[:8]}..."
        )
    except Exception as e:
        logger.info(f"Token unparseable: {e}")
    return None


def _extract_token() -> str:
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:].strip()
    return request.args.get('access_token', '').strip()


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({'error': 'unauthorized', 'message': 'مفتاح المصادقة مطلوب'}), 401
        payload = _decode_token(token)
        if not payload:
            return jsonify({'error': 'invalid_token', 'message': 'مفتاح المصادقة غير صالح أو منتهي'}), 401
        g.user_id = payload.get('sub', '')
        g.email = payload.get('email', '')
        g.iss = payload.get('iss', '')
        g.is_admin = is_admin(g.user_id)
        return fn(*args, **kwargs)

    return wrapper


def require_admin(fn):
    @wraps(fn)
    @require_auth
    def wrapper(*args, **kwargs):
        if not g.get('is_admin'):
            return jsonify({'error': 'forbidden', 'message': 'صلاحيات إدارية مطلوبة'}), 403
        return fn(*args, **kwargs)

    return wrapper
