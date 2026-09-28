from flask import Blueprint, request, jsonify
from backend.app.extensions import db
from backend.app.models.competency import (
    Role,
    Competency,
    RoleCompetency,
    Prerequisite,
    check_for_prerequisite_cycle,
    CycleDetectedError,
    SelfReferenceError
)
from backend.app.utils.auth import role_required

framework_bp = Blueprint("framework", __name__, url_prefix="/api")


# ==========================================
# Competency CRUD Endpoints
# ==========================================

@framework_bp.route("/competencies", methods=["GET"])
@role_required()
def list_competencies():
    """List all competencies with their prerequisite dependencies (open to all authenticated users)."""
    competencies = Competency.query.order_by(Competency.name.asc()).all()
    return jsonify({
        "competencies": [comp.to_dict(include_prerequisites=True) for comp in competencies]
    }), 200


@framework_bp.route("/competencies/<int:competency_id>", methods=["GET"])
@role_required()
def get_competency(competency_id):
    """Get single competency details (open to all authenticated users)."""
    comp = db.session.get(Competency, competency_id)
    if not comp:
        return jsonify({"error": "Not Found", "message": f"Competency {competency_id} not found"}), 404
    return jsonify({"competency": comp.to_dict(include_prerequisites=True)}), 200


@framework_bp.route("/competencies", methods=["POST"])
@role_required("admin")
def create_competency():
    """Create a new competency (admin only)."""
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    description = data.get("description", "")

    if not name or not isinstance(name, str) or not name.strip():
        return jsonify({"error": "Bad Request", "message": "Field 'name' is required"}), 400

    clean_name = name.strip()
    if Competency.query.filter_by(name=clean_name).first():
        return jsonify({"error": "Conflict", "message": f"Competency '{clean_name}' already exists"}), 409

    comp = Competency(name=clean_name, description=description.strip() if description else None)
    db.session.add(comp)
    db.session.commit()

    return jsonify({
        "message": "Competency created successfully",
        "competency": comp.to_dict(include_prerequisites=True)
    }), 201


@framework_bp.route("/competencies/<int:competency_id>", methods=["PUT"])
@role_required("admin")
def update_competency(competency_id):
    """Update an existing competency (admin only)."""
    comp = db.session.get(Competency, competency_id)
    if not comp:
        return jsonify({"error": "Not Found", "message": f"Competency {competency_id} not found"}), 404

    data = request.get_json(silent=True) or {}
    name = data.get("name")
    description = data.get("description")

    if name is not None:
        if not isinstance(name, str) or not name.strip():
            return jsonify({"error": "Bad Request", "message": "Field 'name' cannot be empty"}), 400
        clean_name = name.strip()
        existing = Competency.query.filter_by(name=clean_name).first()
        if existing and existing.id != competency_id:
            return jsonify({"error": "Conflict", "message": f"Competency '{clean_name}' already exists"}), 409
        comp.name = clean_name

    if description is not None:
        comp.description = description.strip() if isinstance(description, str) else description

    db.session.commit()
    return jsonify({
        "message": "Competency updated successfully",
        "competency": comp.to_dict(include_prerequisites=True)
    }), 200


@framework_bp.route("/competencies/<int:competency_id>", methods=["DELETE"])
@role_required("admin")
def delete_competency(competency_id):
    """Delete a competency and its associated prerequisites (admin only)."""
    comp = db.session.get(Competency, competency_id)
    if not comp:
        return jsonify({"error": "Not Found", "message": f"Competency {competency_id} not found"}), 404

    db.session.delete(comp)
    db.session.commit()
    return jsonify({"message": f"Competency {competency_id} deleted successfully"}), 200


# ==========================================
# Role CRUD Endpoints
# ==========================================

@framework_bp.route("/roles", methods=["GET"])
@role_required()
def list_roles():
    """List all job roles (open to all authenticated users)."""
    roles = Role.query.order_by(Role.name.asc()).all()
    return jsonify({"roles": [role.to_dict() for role in roles]}), 200


@framework_bp.route("/roles/<int:role_id>", methods=["GET"])
@role_required()
def get_role(role_id):
    """Get single job role details (open to all authenticated users)."""
    role = db.session.get(Role, role_id)
    if not role:
        return jsonify({"error": "Not Found", "message": f"Role {role_id} not found"}), 404
    return jsonify({"role": role.to_dict()}), 200


@framework_bp.route("/roles", methods=["POST"])
@role_required("admin")
def create_role():
    """Create a new job role (admin only)."""
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    description = data.get("description", "")

    if not name or not isinstance(name, str) or not name.strip():
        return jsonify({"error": "Bad Request", "message": "Field 'name' is required"}), 400

    clean_name = name.strip()
    if Role.query.filter_by(name=clean_name).first():
        return jsonify({"error": "Conflict", "message": f"Role '{clean_name}' already exists"}), 409

    role = Role(name=clean_name, description=description.strip() if description else None)
    db.session.add(role)
    db.session.commit()

    return jsonify({
        "message": "Role created successfully",
        "role": role.to_dict()
    }), 201


@framework_bp.route("/roles/<int:role_id>", methods=["PUT"])
@role_required("admin")
def update_role(role_id):
    """Update a job role (admin only)."""
    role = db.session.get(Role, role_id)
    if not role:
        return jsonify({"error": "Not Found", "message": f"Role {role_id} not found"}), 404

    data = request.get_json(silent=True) or {}
    name = data.get("name")
    description = data.get("description")

    if name is not None:
        if not isinstance(name, str) or not name.strip():
            return jsonify({"error": "Bad Request", "message": "Field 'name' cannot be empty"}), 400
        clean_name = name.strip()
        existing = Role.query.filter_by(name=clean_name).first()
        if existing and existing.id != role_id:
            return jsonify({"error": "Conflict", "message": f"Role '{clean_name}' already exists"}), 409
        role.name = clean_name

    if description is not None:
        role.description = description.strip() if isinstance(description, str) else description

    db.session.commit()
    return jsonify({
        "message": "Role updated successfully",
        "role": role.to_dict()
    }), 200


@framework_bp.route("/roles/<int:role_id>", methods=["DELETE"])
@role_required("admin")
def delete_role(role_id):
    """Delete a job role (admin only)."""
    role = db.session.get(Role, role_id)
    if not role:
        return jsonify({"error": "Not Found", "message": f"Role {role_id} not found"}), 404

    db.session.delete(role)
    db.session.commit()
    return jsonify({"message": f"Role {role_id} deleted successfully"}), 200


# ==========================================
# Role Competency Mapping Endpoints
# ==========================================

@framework_bp.route("/roles/<int:role_id>/competencies", methods=["GET"])
@role_required()
def get_role_competencies(role_id):
    """Get required competencies and levels for a specific role (open to all authenticated users)."""
    role = db.session.get(Role, role_id)
    if not role:
        return jsonify({"error": "Not Found", "message": f"Role {role_id} not found"}), 404

    return jsonify({
        "role_id": role.id,
        "role_name": role.name,
        "competencies": [rc.to_dict() for rc in role.role_competencies]
    }), 200


@framework_bp.route("/roles/<int:role_id>/competencies", methods=["POST", "PUT"])
@role_required("admin")
def set_role_competencies(role_id):
    """
    Set or update required competency levels (1-5) for a role (admin only).
    Accepts single object: {"competency_id": 1, "required_level": 3}
    or a list of objects: [{"competency_id": 1, "required_level": 3}, ...]
    """
    role = db.session.get(Role, role_id)
    if not role:
        return jsonify({"error": "Not Found", "message": f"Role {role_id} not found"}), 404

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Bad Request", "message": "JSON body is required"}), 400

    items = data if isinstance(data, list) else [data]
    if not items:
        return jsonify({"error": "Bad Request", "message": "Empty competency list provided"}), 400

    updated = []
    for item in items:
        if not isinstance(item, dict):
            return jsonify({"error": "Bad Request", "message": "Each competency entry must be an object"}), 400

        competency_id = item.get("competency_id")
        required_level = item.get("required_level")

        if competency_id is None or required_level is None:
            return jsonify({
                "error": "Bad Request",
                "message": "Both 'competency_id' and 'required_level' are required"
            }), 400

        try:
            competency_id = int(competency_id)
            required_level = int(required_level)
        except (ValueError, TypeError):
            return jsonify({"error": "Bad Request", "message": "'competency_id' and 'required_level' must be integers"}), 400

        if not (1 <= required_level <= 5):
            return jsonify({
                "error": "Bad Request",
                "message": f"Invalid required_level '{required_level}'. Must be between 1 and 5"
            }), 400

        comp = db.session.get(Competency, competency_id)
        if not comp:
            return jsonify({"error": "Not Found", "message": f"Competency {competency_id} not found"}), 404

        rc = RoleCompetency.query.filter_by(role_id=role_id, competency_id=competency_id).first()
        if rc:
            rc.required_level = required_level
        else:
            rc = RoleCompetency(role_id=role_id, competency_id=competency_id, required_level=required_level)
            db.session.add(rc)

        updated.append(rc)

    db.session.commit()
    return jsonify({
        "message": f"Updated {len(updated)} competency requirement(s) for role {role.name}",
        "role_id": role.id,
        "competencies": [rc.to_dict() for rc in role.role_competencies]
    }), 200


@framework_bp.route("/roles/<int:role_id>/competencies/<int:competency_id>", methods=["DELETE"])
@role_required("admin")
def remove_role_competency(role_id, competency_id):
    """Remove a competency requirement from a role (admin only)."""
    rc = RoleCompetency.query.filter_by(role_id=role_id, competency_id=competency_id).first()
    if not rc:
        return jsonify({
            "error": "Not Found",
            "message": f"Competency {competency_id} is not associated with role {role_id}"
        }), 404

    db.session.delete(rc)
    db.session.commit()
    return jsonify({"message": f"Competency {competency_id} removed from role {role_id}"}), 200


# ==========================================
# Prerequisites Endpoints
# ==========================================

@framework_bp.route("/prerequisites", methods=["GET"])
@role_required()
def list_prerequisites():
    """List all competency prerequisite pairs (open to all authenticated users)."""
    prereqs = Prerequisite.query.all()
    return jsonify({"prerequisites": [p.to_dict() for p in prereqs]}), 200


@framework_bp.route("/prerequisites", methods=["POST"])
@role_required("admin")
def add_prerequisite():
    """
    Add a prerequisite dependency: requires_competency_id must precede competency_id (admin only).
    Rejects self-references and cycles using NetworkX.
    """
    data = request.get_json(silent=True) or {}
    competency_id = data.get("competency_id")
    requires_competency_id = data.get("requires_competency_id")

    if competency_id is None or requires_competency_id is None:
        return jsonify({
            "error": "Bad Request",
            "message": "Both 'competency_id' and 'requires_competency_id' are required"
        }), 400

    try:
        competency_id = int(competency_id)
        requires_competency_id = int(requires_competency_id)
    except (ValueError, TypeError):
        return jsonify({
            "error": "Bad Request",
            "message": "'competency_id' and 'requires_competency_id' must be integers"
        }), 400

    # Self-reference rejection
    if competency_id == requires_competency_id:
        return jsonify({
            "error": "Bad Request",
            "message": "A competency cannot require itself as a prerequisite"
        }), 400

    # Validate existence of both competencies
    comp = db.session.get(Competency, competency_id)
    if not comp:
        return jsonify({"error": "Not Found", "message": f"Competency {competency_id} not found"}), 404

    req_comp = db.session.get(Competency, requires_competency_id)
    if not req_comp:
        return jsonify({"error": "Not Found", "message": f"Prerequisite competency {requires_competency_id} not found"}), 404

    # Check for existing duplicate
    existing = Prerequisite.query.filter_by(
        competency_id=competency_id,
        requires_competency_id=requires_competency_id
    ).first()
    if existing:
        return jsonify({
            "error": "Conflict",
            "message": f"Competency '{comp.name}' already has '{req_comp.name}' as a prerequisite"
        }), 409

    # Cycle detection using NetworkX
    try:
        check_for_prerequisite_cycle(competency_id, requires_competency_id)
    except (CycleDetectedError, SelfReferenceError) as e:
        return jsonify({"error": "Bad Request", "message": str(e)}), 400

    prereq = Prerequisite(competency_id=competency_id, requires_competency_id=requires_competency_id, validate_cycle=False)
    db.session.add(prereq)
    db.session.commit()

    return jsonify({
        "message": "Prerequisite added successfully",
        "prerequisite": prereq.to_dict()
    }), 201


@framework_bp.route("/prerequisites/<int:prereq_id>", methods=["DELETE"])
@role_required("admin")
def delete_prerequisite_by_id(prereq_id):
    """Remove a prerequisite dependency by ID (admin only)."""
    prereq = db.session.get(Prerequisite, prereq_id)
    if not prereq:
        return jsonify({"error": "Not Found", "message": f"Prerequisite {prereq_id} not found"}), 404

    db.session.delete(prereq)
    db.session.commit()
    return jsonify({"message": f"Prerequisite {prereq_id} removed successfully"}), 200


@framework_bp.route("/prerequisites", methods=["DELETE"])
@role_required("admin")
def delete_prerequisite_by_pair():
    """Remove a prerequisite dependency by competency pair (admin only)."""
    data = request.get_json(silent=True) or {}
    competency_id = data.get("competency_id")
    requires_competency_id = data.get("requires_competency_id")

    if not competency_id or not requires_competency_id:
        return jsonify({
            "error": "Bad Request",
            "message": "Both 'competency_id' and 'requires_competency_id' are required"
        }), 400

    prereq = Prerequisite.query.filter_by(
        competency_id=int(competency_id),
        requires_competency_id=int(requires_competency_id)
    ).first()

    if not prereq:
        return jsonify({"error": "Not Found", "message": "Prerequisite relationship not found"}), 404

    db.session.delete(prereq)
    db.session.commit()
    return jsonify({"message": "Prerequisite removed successfully"}), 200


# ==========================================
# Framework Summary Endpoint
# ==========================================

@framework_bp.route("/roles/<int:role_id>/framework", methods=["GET"])
@role_required()
def get_role_framework(role_id):
    """
    Get the complete framework for a job role:
    Returns the role's required competencies, their levels, and their prerequisites in one response.
    """
    role = db.session.get(Role, role_id)
    if not role:
        return jsonify({"error": "Not Found", "message": f"Role {role_id} not found"}), 404

    competencies_data = []
    for rc in role.role_competencies:
        comp = rc.competency
        if not comp:
            continue

        prereq_list = [
            {
                "id": p.requires_competency.id,
                "name": p.requires_competency.name
            }
            for p in comp.prerequisites if p.requires_competency
        ]

        competencies_data.append({
            "id": comp.id,
            "name": comp.name,
            "description": comp.description,
            "required_level": rc.required_level,
            "prerequisites": prereq_list
        })

    return jsonify({
        "role": role.to_dict(),
        "competencies": competencies_data
    }), 200
