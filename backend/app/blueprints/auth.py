import re
from flask import Blueprint, request, jsonify, g
from backend.app.extensions import db, limiter
from backend.app.models.user import User
from backend.app.utils.auth import generate_token, role_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user account."""
    data = request.get_json(silent=True) or {}

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "learner")

    if not name or not isinstance(name, str) or not name.strip():
        return jsonify({"error": "Bad Request", "message": "Field 'name' is required"}), 400

    if not email or not isinstance(email, str) or not email.strip():
        return jsonify({"error": "Bad Request", "message": "Field 'email' is required"}), 400

    normalized_email = email.strip().lower()
    if not re.match(EMAIL_REGEX, normalized_email):
        return jsonify({"error": "Bad Request", "message": "Invalid email address format"}), 400

    if not password or not isinstance(password, str) or len(password) < 6:
        return jsonify({
            "error": "Bad Request",
            "message": "Field 'password' is required and must be at least 6 characters"
        }), 400

    if role not in User.VALID_ROLES:
        return jsonify({
            "error": "Bad Request",
            "message": f"Invalid role '{role}'. Allowed roles are: {', '.join(sorted(User.VALID_ROLES))}"
        }), 400

    if User.query.filter_by(email=normalized_email).first():
        return jsonify({
            "error": "Conflict",
            "message": f"User with email '{normalized_email}' already exists"
        }), 409

    user = User(name=name, email=normalized_email, password=password, role=role)
    db.session.add(user)
    db.session.commit()

    token = generate_token(user)

    return jsonify({
        "message": "User registered successfully",
        "token": token,
        "user": user.to_dict()
    }), 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("20 per minute")
def login():
    """Authenticate a user and return a JWT access token."""
    data = request.get_json(silent=True) or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "error": "Bad Request",
            "message": "Both 'email' and 'password' are required"
        }), 400

    normalized_email = email.strip().lower()
    user = User.query.filter_by(email=normalized_email).first()

    if not user or not user.check_password(password):
        return jsonify({
            "error": "Unauthorized",
            "message": "Invalid email or password"
        }), 401

    token = generate_token(user)

    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": user.to_dict()
    }), 200


@auth_bp.route("/me", methods=["GET"])
@role_required()
def me():
    """Get the current authenticated user profile."""
    return jsonify({
        "user": g.current_user.to_dict()
    }), 200


# Dedicated role-protected endpoints for testing and role verification
@auth_bp.route("/role-test/admin", methods=["GET"])
@role_required("admin")
def admin_only_endpoint():
    """Accessible only by admin users."""
    return jsonify({
        "message": "Admin access granted",
        "user": g.current_user.to_dict()
    }), 200


@auth_bp.route("/role-test/trainer", methods=["GET"])
@role_required("trainer", "admin")
def trainer_or_admin_endpoint():
    """Accessible by trainers and admins."""
    return jsonify({
        "message": "Trainer/Admin access granted",
        "user": g.current_user.to_dict()
    }), 200


@auth_bp.route("/role-test/learner", methods=["GET"])
@role_required("learner")
def learner_only_endpoint():
    """Accessible only by learners."""
    return jsonify({
        "message": "Learner access granted",
        "user": g.current_user.to_dict()
    }), 200
