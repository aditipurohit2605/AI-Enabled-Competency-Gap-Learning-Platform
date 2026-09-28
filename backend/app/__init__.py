import os
from flask import Flask
from backend.app.config import config_by_name, Config
from backend.app.extensions import db
from backend.app.blueprints.health import health_bp
from backend.app.blueprints.auth import auth_bp
from backend.app.blueprints.framework import framework_bp
from backend.app.blueprints.profile import profile_bp
from backend.app.blueprints.gap import gap_bp
from backend.app.blueprints.path import path_bp
from backend.app.blueprints.assessment import assessment_bp
# Import models to ensure they are registered with SQLAlchemy metadata
import backend.app.models  # noqa: F401


def create_app(config_object=None, config_name=None):
    """Application factory for the Flask backend."""
    app = Flask(__name__)

    # Apply configuration
    if config_object:
        app.config.from_object(config_object)
    elif config_name:
        selected_config = config_by_name.get(config_name, Config)
        app.config.from_object(selected_config)
    else:
        env = os.getenv("FLASK_ENV", "development").lower()
        selected_config = config_by_name.get(env, config_by_name["default"])
        app.config.from_object(selected_config)

    # Initialize extensions
    db.init_app(app)

    # Configure CORS
    from flask_cors import CORS
    cors_origins = [o.strip() for o in app.config.get("CORS_ORIGINS", "*").split(",") if o.strip()]
    CORS(app, origins=cors_origins, supports_credentials=True)

    # Direct /api/me route
    from flask import jsonify, g
    from backend.app.utils.auth import role_required

    @app.route("/api/me", methods=["GET"])
    @role_required()
    def get_me():
        user = g.current_user
        return jsonify({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "user": user.to_dict()
        }), 200

    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(framework_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(gap_bp)
    app.register_blueprint(path_bp)
    app.register_blueprint(assessment_bp)

    # Ensure tables are created if running standalone
    with app.app_context():
        db.create_all()

    return app
