from flask import Blueprint, request, jsonify, g
from backend.app.utils.auth import role_required
from backend.services.gap import analyze_role_gap

gap_bp = Blueprint("gap", __name__, url_prefix="/api")


@gap_bp.route("/gap", methods=["GET"])
@role_required()
def get_gap_analysis():
    """
    Perform competency gap analysis for the logged-in user against a target job role.
    Query parameters:
      - role_id: ID of the role to compare against (required)
    """
    role_id_raw = request.args.get("role_id")
    if not role_id_raw:
        return jsonify({
            "error": "Bad Request",
            "message": "Query parameter 'role_id' is required"
        }), 400

    try:
        role_id = int(role_id_raw)
    except (ValueError, TypeError):
        return jsonify({
            "error": "Bad Request",
            "message": "Query parameter 'role_id' must be an integer"
        }), 400

    result = analyze_role_gap(user_id=g.current_user.id, role_id=role_id)
    if result is None:
        return jsonify({
            "error": "Not Found",
            "message": f"Role {role_id} not found"
        }), 404

    return jsonify(result), 200
