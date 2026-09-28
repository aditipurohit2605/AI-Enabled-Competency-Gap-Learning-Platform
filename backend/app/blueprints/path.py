from flask import Blueprint, request, jsonify, g
from backend.app.extensions import db
from backend.app.models.learning import Course, UserCourseProgress
from backend.app.models.competency import Role
from backend.app.utils.auth import role_required
from backend.services.path_planner import generate_learning_path

path_bp = Blueprint("path", __name__, url_prefix="/api/path")


@path_bp.route("", methods=["GET"])
@role_required()
def get_path():
    """
    Generate an optimal, prerequisite-aware learning path for the logged-in user
    towards a target job role.
    Query parameters:
      - role_id: ID of the job role (required)
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

    role = db.session.get(Role, role_id)
    if not role:
        return jsonify({
            "error": "Not Found",
            "message": f"Role {role_id} not found"
        }), 404

    path_data = generate_learning_path(user_id=g.current_user.id, role_id=role_id)
    return jsonify(path_data), 200


@path_bp.route("/progress", methods=["POST"])
@role_required()
def update_course_progress():
    """
    Record or update learner progress on a course:
    Body: {"course_id": int, "status": "planned" | "in_progress" | "completed"}
    """
    data = request.get_json(silent=True) or {}
    course_id = data.get("course_id")
    status = data.get("status")

    if course_id is None or not status:
        return jsonify({
            "error": "Bad Request",
            "message": "Fields 'course_id' and 'status' are required"
        }), 400

    try:
        course_id = int(course_id)
    except (ValueError, TypeError):
        return jsonify({
            "error": "Bad Request",
            "message": "Field 'course_id' must be an integer"
        }), 400

    if status not in UserCourseProgress.VALID_STATUSES:
        return jsonify({
            "error": "Bad Request",
            "message": f"Invalid status '{status}'. Allowed statuses: {', '.join(sorted(UserCourseProgress.VALID_STATUSES))}"
        }), 400

    course = db.session.get(Course, course_id)
    if not course:
        return jsonify({
            "error": "Not Found",
            "message": f"Course {course_id} not found"
        }), 404

    user_id = g.current_user.id
    progress = UserCourseProgress.query.filter_by(user_id=user_id, course_id=course_id).first()

    if progress:
        progress.status = status
    else:
        progress = UserCourseProgress(user_id=user_id, course_id=course_id, status=status)
        db.session.add(progress)

    db.session.commit()

    return jsonify({
        "message": f"Course progress updated to '{status}'",
        "progress": progress.to_dict()
    }), 200


@path_bp.route("/progress", methods=["GET"])
@role_required()
def get_user_progress():
    """
    Get all course progress records for the authenticated learner.
    """
    user_id = g.current_user.id
    records = UserCourseProgress.query.filter_by(user_id=user_id).all()

    return jsonify({
        "user_id": user_id,
        "total_records": len(records),
        "progress": [r.to_dict() for r in records]
    }), 200
