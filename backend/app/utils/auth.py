from functools import wraps
from datetime import datetime, timezone, timedelta
import jwt
from flask import request, jsonify, current_app, g
from backend.app.extensions import db
from backend.app.models.user import User


def generate_token(user, expires_in=None):
    """
    Generate a signed JWT token for a user.
    user can be a User model instance or a dict with id, email, role, name.
    """
    secret_key = current_app.config.get("JWT_SECRET_KEY", "fallback-secret-key")
    if expires_in is None:
        expires_in = current_app.config.get("JWT_EXPIRATION_SECONDS", 86400)

    now = datetime.now(timezone.utc)
    user_id = user.id if hasattr(user, "id") else user.get("id")
    email = user.email if hasattr(user, "email") else user.get("email")
    role = user.role if hasattr(user, "role") else user.get("role")
    name = user.name if hasattr(user, "name") else user.get("name")

    payload = {
        "sub": str(user_id),
        "user_id": user_id,
        "email": email,
        "role": role,
        "name": name,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in)
    }

    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token


def decode_token(token):
    """
    Decode and verify a JWT token.
    Returns decoded payload or raises jwt exceptions.
    """
    secret_key = current_app.config.get("JWT_SECRET_KEY", "fallback-secret-key")
    payload = jwt.decode(token, secret_key, algorithms=["HS256"])
    return payload


def get_token_from_header():
    """Extract Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def role_required(*allowed_roles):
    """
    Decorator to protect routes with JWT authentication and role authorization.
    Can be used as:
      @role_required('admin')
      @role_required('trainer', 'admin')
      @role_required(['trainer', 'admin'])
      @role_required()  # Any authenticated user
    """
    # Flatten if arguments passed as a list/tuple
    flattened_roles = []
    for r in allowed_roles:
        if isinstance(r, (list, tuple, set)):
            flattened_roles.extend(r)
        else:
            flattened_roles.append(r)

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = get_token_from_header()
            if not token:
                return jsonify({
                    "error": "Unauthorized",
                    "message": "Authorization header missing or invalid format. Expected 'Bearer <token>'"
                }), 401

            try:
                payload = decode_token(token)
            except jwt.ExpiredSignatureError:
                return jsonify({
                    "error": "Unauthorized",
                    "message": "Token has expired"
                }), 401
            except jwt.InvalidTokenError:
                return jsonify({
                    "error": "Unauthorized",
                    "message": "Invalid token"
                }), 401

            user_id = payload.get("user_id") or payload.get("sub")
            try:
                user_id_int = int(user_id)
            except (ValueError, TypeError):
                user_id_int = None
            user = db.session.get(User, user_id_int) if user_id_int is not None else None
            if not user:
                return jsonify({
                    "error": "Unauthorized",
                    "message": "User associated with token no longer exists"
                }), 401

            # Check role permission if specific roles are required
            if flattened_roles and user.role not in flattened_roles:
                return jsonify({
                    "error": "Forbidden",
                    "message": f"Access denied. Requires one of roles: {', '.join(flattened_roles)}"
                }), 403

            # Store current user in Flask g
            g.current_user = user
            return fn(*args, **kwargs)

        return wrapper

    return decorator
