"""Supabase JWT verification middleware.

Supports both:
- New asymmetric JWT signing keys (RS256/ES256) via JWKS endpoint
- Legacy HS256 with shared secret

Tries asymmetric first (the default for new Supabase projects), falls back
to HS256 if SUPABASE_JWT_SECRET is set and asymmetric verification fails.
"""
import logging
from functools import wraps

import jwt
from flask import g, jsonify, request

from config import Config, is_admin

logger = logging.getLogger(__name__)

_jwks_client: jwt.PyJWKClient | None = None


def _get_jwks_client() -> jwt.PyJWKClient | None:
    global _jwks_client
    if _jwks_client is not None:
        return _jwks_client
    if not Config.SUPABASE_URL:
        return None
    jwks_url = f"{Config.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
    try:
        _jwks_client = jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
        return _jwks_client
    except Exception as e:
        logger.warning(f"Could not init JWKS client: {e}")
        return None


def _decode_asymmetric(token: str) -> dict | None:
    client = _get_jwks_client()
    if not client:
        return None
    try:
        signing_key = client.get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=['RS256', 'ES256'],
            audience=Config.SUPABASE_JWT_AUDIENCE,
        )
    except jwt.ExpiredSignatureError:
        logger.info("JWT expired (asymmetric)")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Asymmetric verify failed: {e}")
        return None
    except Exception as e:
        logger.debug(f"JWKS lookup failed: {e}")
        return None


def _decode_symmetric(token: str) -> dict | None:
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
        logger.debug(f"Symmetric verify failed: {e}")
        return None


def _decode_token(token: str) -> dict | None:
    payload = _decode_asymmetric(token)
    if payload:
        return payload
    payload = _decode_symmetric(token)
    if payload:
        return payload
    if not Config.SUPABASE_JWT_SECRET and not Config.SUPABASE_URL:
        logger.error("Neither SUPABASE_URL nor SUPABASE_JWT_SECRET is configured")
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
