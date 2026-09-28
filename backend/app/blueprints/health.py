from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
@health_bp.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint to verify backend service availability."""
    return jsonify({
        "status": "ok",
        "service": "competency-gap-learning-platform",
        "version": "1.0.0"
    }), 200
