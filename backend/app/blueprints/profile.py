import json
from flask import Blueprint, request, jsonify, g
from backend.app.extensions import db
from backend.app.models.competency import Competency, UserSkill
from backend.app.utils.auth import role_required
from backend.services.skill_extractor import extract_skills_from_profile
from backend.services.gap import get_user_combined_skills

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")


@profile_bp.route("/analyze", methods=["POST"])
@role_required()
def analyze_profile():
    """
    Extract skills from profile text:
      - Semantically matches sentences against all competencies
      - Estimates level (1-4) with transparent reasons and evidence
      - Saves/updates results in UserSkill with source='profile'
    """
    data = request.get_json(silent=True) or {}
    text = data.get("text")
    threshold = float(data.get("threshold", 0.55))

    if not text or not isinstance(text, str) or not text.strip():
        return jsonify({
            "error": "Bad Request",
            "message": "Field 'text' is required and must contain profile content"
        }), 400

    competencies = Competency.query.all()
    if not competencies:
        return jsonify({
            "message": "No competencies configured in the system",
            "extracted_count": 0,
            "skills": []
        }), 200

    # Extract skills
    extracted = extract_skills_from_profile(text.strip(), competencies, threshold=threshold)

    # Persist extracted skills as source='profile'
    user_id = g.current_user.id
    for item in extracted:
        comp_id = item["competency_id"]
        evidence_payload = json.dumps({
            "sentences": item["evidence"],
            "reasons": item["reasons"]
        })

        us = UserSkill.query.filter_by(
            user_id=user_id,
            competency_id=comp_id,
            source="profile"
        ).first()

        if us:
            us.level = float(item["level"])
            us.evidence = evidence_payload
        else:
            us = UserSkill(
                user_id=user_id,
                competency_id=comp_id,
                level=float(item["level"]),
                evidence=evidence_payload,
                source="profile"
            )
            db.session.add(us)

    db.session.commit()

    return jsonify({
        "message": f"Successfully extracted {len(extracted)} competencies from profile",
        "extracted_count": len(extracted),
        "skills": extracted
    }), 200


@profile_bp.route("/self-assessment", methods=["PUT", "POST"])
@profile_bp.route("/self-assess", methods=["POST", "PUT"])
@role_required()
def self_assessment():
    """
    Submit or update self-assessed competency levels (1-5):
    Accepts object: {"competency_id": level, ...}, {"ratings": {...}}, or list of {"competency_id": x, "level": y}
    Saves to UserSkill with source='self'.
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Bad Request", "message": "JSON body is required"}), 400

    user_id = g.current_user.id
    saved = []

    # Handle {"ratings": {...}} format from frontend
    if isinstance(data, dict) and "ratings" in data and isinstance(data["ratings"], dict):
        entries = list(data["ratings"].items())
    elif isinstance(data, dict):
        entries = list(data.items())
    elif isinstance(data, list):
        entries = []
        for item in data:
            if isinstance(item, dict) and "competency_id" in item and "level" in item:
                entries.append((item["competency_id"], item["level"]))
            else:
                return jsonify({
                    "error": "Bad Request",
                    "message": "Each list entry must contain 'competency_id' and 'level'"
                }), 400
    else:
        return jsonify({"error": "Bad Request", "message": "Expected JSON object or array"}), 400

    if not entries:
        return jsonify({"error": "Bad Request", "message": "No competency levels provided"}), 400

    for comp_id_raw, level_raw in entries:
        try:
            comp_id = int(comp_id_raw)
            level = float(level_raw)
        except (ValueError, TypeError):
            return jsonify({
                "error": "Bad Request",
                "message": f"Invalid competency ID '{comp_id_raw}' or level '{level_raw}'. Must be numeric."
            }), 400

        if not (1.0 <= level <= 5.0):
            return jsonify({
                "error": "Bad Request",
                "message": f"Level for competency {comp_id} must be between 1 and 5"
            }), 400

        comp = db.session.get(Competency, comp_id)
        if not comp:
            return jsonify({"error": "Not Found", "message": f"Competency {comp_id} not found"}), 404

        us = UserSkill.query.filter_by(
            user_id=user_id,
            competency_id=comp_id,
            source="self"
        ).first()

        evidence_note = f"Self-assessed rating of level {level:.0f}"
        if us:
            us.level = level
            us.evidence = evidence_note
        else:
            us = UserSkill(
                user_id=user_id,
                competency_id=comp_id,
                level=level,
                evidence=evidence_note,
                source="self"
            )
            db.session.add(us)

        saved.append({
            "competency_id": comp.id,
            "competency_name": comp.name,
            "level": level,
            "source": "self"
        })

    db.session.commit()

    return jsonify({
        "message": f"Updated self-assessment for {len(saved)} competencies",
        "updated_count": len(saved),
        "skills": saved
    }), 200


@profile_bp.route("/skills", methods=["GET"])
@role_required()
def get_user_skills():
    """
    Get current combined skills for the authenticated user:
    Averages profile and self-assessment scores when both exist,
    recording contributing sources and evidence.
    """
    user_id = g.current_user.id
    combined_skills = get_user_combined_skills(user_id)

    # Sort by competency name
    skill_list = sorted(list(combined_skills.values()), key=lambda x: (x["competency_name"] or ""))

    return jsonify({
        "user_id": user_id,
        "total_skills": len(skill_list),
        "skills": skill_list
    }), 200


@profile_bp.route("/skills", methods=["POST", "PUT"])
@role_required()
def save_user_skills():
    """
    Explicitly save or update extracted profile skills.
    Accepts: {"skills": [{"competency_id": ..., "level": ..., "evidence": ...}, ...]}
    """
    data = request.get_json(silent=True) or {}
    skills_data = data.get("skills", [])
    if not isinstance(skills_data, list):
        return jsonify({"error": "Bad Request", "message": "Expected list of skills"}), 400

    user_id = g.current_user.id
    saved = []

    for item in skills_data:
        comp_id = item.get("competency_id")
        level = item.get("level")
        if comp_id is None or level is None:
            continue

        comp = db.session.get(Competency, comp_id)
        if not comp:
            continue

        evidence = item.get("evidence")
        evidence_str = json.dumps(evidence) if isinstance(evidence, (dict, list)) else str(evidence or "")

        us = UserSkill.query.filter_by(
            user_id=user_id,
            competency_id=comp_id,
            source="profile"
        ).first()

        if us:
            us.level = float(level)
            us.evidence = evidence_str
        else:
            us = UserSkill(
                user_id=user_id,
                competency_id=comp_id,
                level=float(level),
                evidence=evidence_str,
                source="profile"
            )
            db.session.add(us)

        saved.append({"competency_id": comp_id, "level": float(level)})

    db.session.commit()
    return jsonify({
        "message": f"Successfully saved {len(saved)} skills to profile",
        "saved_count": len(saved),
        "skills": saved
    }), 200
