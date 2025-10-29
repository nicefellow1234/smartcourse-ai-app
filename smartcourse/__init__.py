from __future__ import annotations

import os
from flask import Flask

from .config import get_config
from .extensions import db, cors
from .views import ui_bp
from .api import api_bp


def create_app(config_name: str | None = None) -> Flask:
    """Application factory for SmartCourse."""
    app = Flask(__name__, instance_relative_config=True, template_folder="../templates", static_folder="../static")

    config_obj = get_config(config_name)
    app.config.from_object(config_obj)

    # Ensure instance folder exists for SQLite database and persisted files
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Set default SQLite database path if not explicitly provided
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(app.instance_path, 'smartcourse.db')}"
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)

    register_extensions(app)
    register_blueprints(app)

    with app.app_context():
        db.create_all()

    return app


def register_extensions(app: Flask) -> None:
    db.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(ui_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
