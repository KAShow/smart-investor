"""Supabase JWT verification middleware.

Verifies the Authorization: Bearer <token> header against SUPABASE_JWT_SECRET.
Decoded user_id (sub) and email land in flask.g for handlers to use.
"""
import logging
from functools import wraps

import jwt
from flask import g, jsonify, request

from config import Config, is_admin

logger = logging.getLogger(__name__)


def _decode_token(token: str) -> dict | None:
    if not Config.SUPABASE_JWT_SECRET:
        logger.error("SUPABASE_JWT_SECRET not configured")
        return None
    try:
        return jwt.decode(
            token,
            Config.SUPABASE_JWT_SECRET,
            algorithms=['HS256'],
            audience=Config.SUPABASE_JWT_AUDIENCE,
        )
    except jwt.ExpiredSignatureError:
        logger.info("JWT expired")
    except jwt.InvalidTokenError as e:
        logger.info(f"Invalid JWT: {e}")
    return None


def _extract_token() -> str:
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:].strip()
    # Fallback: query param ONLY for SSE endpoints (EventSource cannot send headers)
    # Frontend should still use fetch + ReadableStream when possible.
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
