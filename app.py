"""Flask application factory.

Run locally:  python app.py
Production:   gunicorn app:app  (binding & workers configured in render.yaml)
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from flask import Flask, jsonify

from config import Config
from database import cleanup_expired_analyses, init_db

# init_db must run before any module that imports BahrainDataService or database helpers
init_db()

from extensions import init_extensions
from routes import register_blueprints


def _configure_logging():
    level = getattr(logging, Config.LOG_LEVEL, logging.INFO)
    fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    handlers = [logging.StreamHandler(sys.stdout)]
    try:
        file_handler = RotatingFileHandler(
            'debug.log', encoding='utf-8', maxBytes=5 * 1024 * 1024, backupCount=3
        )
        file_handler.setFormatter(fmt)
        handlers.append(file_handler)
    except Exception:
        pass
    for h in handlers:
        h.setFormatter(fmt)
    logging.basicConfig(level=level, handlers=handlers, force=True)


def _start_cleanup_scheduler():
    """Daily background job to delete expired analyses."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(cleanup_expired_analyses, 'interval', hours=24, id='cleanup_expired')
        scheduler.start()
        logging.getLogger(__name__).info("Cleanup scheduler started (24h interval)")
    except ImportError:
        logging.getLogger(__name__).warning("APScheduler not installed; expired-analyses cleanup disabled")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Could not start cleanup scheduler: {e}")


def create_app() -> Flask:
    _configure_logging()
    app = Flask(__name__)
    app.config['JSON_AS_ASCII'] = False
    init_extensions(app)
    register_blueprints(app)

    @app.errorhandler(404)
    def _not_found(_):
        return jsonify({'error': 'not_found'}), 404

    @app.errorhandler(405)
    def _method_not_allowed(_):
        return jsonify({'error': 'method_not_allowed'}), 405

    @app.errorhandler(429)
    def _rate_limited(e):
        return jsonify({
            'error': 'rate_limited',
            'message': 'تم تجاوز الحد الأقصى للطلبات، الرجاء المحاولة لاحقاً',
            'retry_after': getattr(e, 'description', None),
        }), 429

    @app.errorhandler(500)
    def _server_error(e):
        logging.getLogger(__name__).exception("Unhandled error")
        return jsonify({'error': 'internal_error'}), 500

    if os.getenv('ENABLE_CLEANUP_SCHEDULER', '1') == '1':
        _start_cleanup_scheduler()

    return app


app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.DEBUG, use_reloader=False)
