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
from backend.app.blueprints.admin import admin_bp
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
    from backend.app.extensions import limiter
    limiter.init_app(app)

    # Configure CORS
    from flask_cors import CORS
    cors_origins = [o.strip() for o in app.config.get("CORS_ORIGINS", "*").split(",") if o.strip()]
    CORS(app, origins=cors_origins, supports_credentials=True)

    # Startup environment check
    if not app.testing:
        missing_keys = []
        if not os.getenv("SECRET_KEY"):
            missing_keys.append("SECRET_KEY (using dev fallback)")
        if not os.getenv("JWT_SECRET_KEY"):
            missing_keys.append("JWT_SECRET_KEY (using dev fallback)")
        if not os.getenv("GEMINI_API_KEY"):
            missing_keys.append("GEMINI_API_KEY (AI generation requires key or pre-seeded questions)")
        if missing_keys:
            app.logger.warning("[Startup Notice] Missing env vars: %s", ", ".join(missing_keys))

    # Standard JSON Error Handlers
    from flask import jsonify, g

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad Request", "message": getattr(e, "description", str(e))}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not Found", "message": getattr(e, "description", "The requested resource was not found")}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method Not Allowed", "message": getattr(e, "description", "The method is not allowed for this URL")}), 405

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({"error": "Rate Limit Exceeded", "message": getattr(e, "description", "Too many requests. Please try again later.")}), 429

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Internal Server Error", "message": "An unexpected server error occurred."}), 500

    # Direct /api/me route
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
    app.register_blueprint(admin_bp)

    # Ensure tables are created if running standalone
    with app.app_context():
        db.create_all()
        # Safe column upgrade for existing SQLite databases
        try:
            with db.engine.connect() as conn:
                doc_cols = [r[1] for r in conn.execute(db.text("PRAGMA table_info(documents)")).fetchall()]
                if doc_cols and "competency_id" not in doc_cols:
                    conn.execute(db.text("ALTER TABLE documents ADD COLUMN competency_id INTEGER"))
                    conn.commit()
                user_cols = [r[1] for r in conn.execute(db.text("PRAGMA table_info(users)")).fetchall()]
                if user_cols and "target_role_id" not in user_cols:
                    conn.execute(db.text("ALTER TABLE users ADD COLUMN target_role_id INTEGER"))
                    conn.commit()
                if user_cols and "created_at" not in user_cols:
                    conn.execute(db.text("ALTER TABLE users ADD COLUMN created_at DATETIME"))
                    conn.commit()
                qa_cols = [r[1] for r in conn.execute(db.text("PRAGMA table_info(quiz_attempts)")).fetchall()]
                if qa_cols and "session_id" not in qa_cols:
                    conn.execute(db.text("ALTER TABLE quiz_attempts ADD COLUMN session_id INTEGER"))
                    conn.commit()
        except Exception:
            pass

    return app
