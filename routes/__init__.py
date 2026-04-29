from flask import Flask

from .analysis import bp as analysis_bp
from .data import bp as data_bp
from .admin import bp as admin_bp


def register_blueprints(app: Flask):
    app.register_blueprint(analysis_bp, url_prefix='/api')
    app.register_blueprint(data_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
