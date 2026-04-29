"""Flask extension singletons configured here so blueprints can import them."""
import logging

from flask import g
from flask_cors import CORS
from flask_limiter import Limiter

from config import Config

logger = logging.getLogger(__name__)


def _user_or_ip_key():
    """Per-user when authenticated, per-IP otherwise."""
    user_id = g.get('user_id') if g else None
    if user_id:
        return f'user:{user_id}'
    from flask import request
    return f'ip:{request.remote_addr or "unknown"}'


cors = CORS(
    resources={r"/api/*": {"origins": Config.CORS_ORIGINS}},
    supports_credentials=False,
    allow_headers=['Authorization', 'Content-Type'],
    expose_headers=['Content-Type'],
    methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
)


limiter = Limiter(
    key_func=_user_or_ip_key,
    storage_uri=Config.REDIS_URL,
    default_limits=[Config.RATE_LIMIT_PER_IP_MINUTE],
    headers_enabled=True,
    swallow_errors=True,
)


def init_extensions(app):
    cors.init_app(app)
    limiter.init_app(app)

    @app.after_request
    def _security_headers(resp):
        resp.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
        resp.headers.setdefault('X-Frame-Options', 'DENY')
        resp.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        resp.headers.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')
        return resp

    return app
