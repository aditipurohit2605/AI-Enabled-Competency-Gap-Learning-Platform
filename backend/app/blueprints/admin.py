from flask import Blueprint, request, jsonify, g
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.competency import Role, Competency, RoleCompetency
from backend.app.models.assessment import QuizSession
from backend.app.utils.auth import role_required
from backend.services.gap import analyze_role_gap, get_user_combined_skills

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/analytics", methods=["GET"])
@role_required("admin")
def get_admin_analytics():
    """
    Admin-only analytics aggregation:
      - Number of learners
      - Average readiness for the selected (or default) role
      - Top 5 most common gaps (competency, average gap, learners affected)
      - Learner by competency matrix with current level (for heatmap)
      - Quiz completion counts and average score per competency
    """
    learners = User.query.filter_by(role="learner").order_by(User.name.asc()).all()
    num_learners = len(learners)

    role_id = request.args.get("role_id")
    target_role = None
    if role_id:
        try:
            target_role = db.session.get(Role, int(role_id))
        except (ValueError, TypeError):
            target_role = None

    if not target_role:
        target_role = Role.query.first()

    all_competencies = Competency.query.order_by(Competency.name.asc()).all()
    competency_headers = [{"id": c.id, "name": c.name} for c in all_competencies]

    # 1. Learner competency matrix & readiness aggregation
    learner_matrix = []
    readiness_scores = []
    gaps_by_comp: dict[int, list[float]] = {}

    for learner in learners:
        skills = get_user_combined_skills(learner.id)
        learner_comp_levels = {}
        for c in all_competencies:
            lvl = skills.get(c.id, {}).get("level", 0.0)
            learner_comp_levels[str(c.id)] = lvl

        learner_matrix.append({
            "learner_id": learner.id,
            "learner_name": learner.name,
            "learner_email": learner.email,
            "competencies": learner_comp_levels
        })

        if target_role:
            analysis = analyze_role_gap(learner.id, target_role.id)
            if analysis:
                readiness_scores.append(analysis.get("readiness_percentage", 0.0))
                for comp_info in analysis.get("competencies", []):
                    c_id = comp_info["competency_id"]
                    gap_val = comp_info["gap"]
                    if c_id not in gaps_by_comp:
                        gaps_by_comp[c_id] = []
                    gaps_by_comp[c_id].append(gap_val)

    avg_readiness = (
        sum(readiness_scores) / len(readiness_scores) if readiness_scores else 0.0
    )

    # 2. Top 5 most common gaps
    comp_map = {c.id: c.name for c in all_competencies}
    top_gaps = []
    for c_id, gap_list in gaps_by_comp.items():
        positive_gaps = [g for g in gap_list if g > 0]
        affected_count = len(positive_gaps)
        avg_gap = (sum(positive_gaps) / affected_count) if affected_count > 0 else 0.0
        if affected_count > 0:
            top_gaps.append({
                "competency_id": c_id,
                "competency_name": comp_map.get(c_id, f"Competency {c_id}"),
                "average_gap": round(avg_gap, 2),
                "learners_affected": affected_count
            })

    # Sort top gaps by number of learners affected (desc), then avg gap (desc)
    top_gaps.sort(key=lambda x: (x["learners_affected"], x["average_gap"]), reverse=True)
    top_5_gaps = top_gaps[:5]

    # 3. Quiz stats per competency
    submitted_sessions = QuizSession.query.filter(QuizSession.submitted_at.isnot(None)).all()
    total_quizzes_taken = len(submitted_sessions)

    quiz_stats_map: dict[int, list[float]] = {}
    for s in submitted_sessions:
        if s.competency_id not in quiz_stats_map:
            quiz_stats_map[s.competency_id] = []
        if s.score_pct is not None:
            quiz_stats_map[s.competency_id].append(s.score_pct)

    quiz_stats_by_competency = []
    for c in all_competencies:
        scores = quiz_stats_map.get(c.id, [])
        quiz_stats_by_competency.append({
            "competency_id": c.id,
            "competency_name": c.name,
            "quiz_count": len(scores),
            "average_score": round(sum(scores) / len(scores), 1) if scores else 0.0
        })

    return jsonify({
        "role_id": target_role.id if target_role else None,
        "role_name": target_role.name if target_role else None,
        "num_learners": num_learners,
        "average_readiness": round(avg_readiness, 1),
        "total_quizzes_taken": total_quizzes_taken,
        "top_gaps": top_5_gaps,
        "learner_matrix": learner_matrix,
        "competency_headers": competency_headers,
        "quiz_stats_by_competency": quiz_stats_by_competency
    }), 200


@admin_bp.route("/users", methods=["GET"])
@role_required("admin")
def list_users():
    """Admin-only list of all users in the system."""
    users = User.query.order_by(User.id.asc()).all()
    return jsonify({
        "users": [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "role": u.role,
                "created_at": u.created_at.isoformat() if hasattr(u, "created_at") and u.created_at else None
            }
            for u in users
        ]
    }), 200
