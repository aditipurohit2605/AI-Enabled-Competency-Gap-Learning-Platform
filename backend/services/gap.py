import json
from backend.app.extensions import db
from backend.app.models.competency import Role, Competency, RoleCompetency, UserSkill, Prerequisite


def get_user_combined_skills(user_id: int) -> dict[int, dict]:
    """
    Get user skills combined across sources (profile, self, etc.).
    When both profile and self assessments exist for a competency,
    calculates their arithmetic average and records contributing sources.
    """
    user_skills = UserSkill.query.filter_by(user_id=user_id).all()

    skills_by_comp: dict[int, dict] = {}
    for us in user_skills:
        comp_id = us.competency_id
        if comp_id not in skills_by_comp:
            skills_by_comp[comp_id] = {
                "competency_id": comp_id,
                "competency_name": us.competency.name if us.competency else None,
                "sources": [],
                "source_levels": {},
                "evidence_list": []
            }

        skills_by_comp[comp_id]["sources"].append(us.source)
        skills_by_comp[comp_id]["source_levels"][us.source] = float(us.level)
        if us.evidence:
            try:
                # Try parsing JSON evidence if present
                parsed_ev = json.loads(us.evidence)
                if isinstance(parsed_ev, dict):
                    skills_by_comp[comp_id]["evidence_list"].extend(parsed_ev.get("sentences", []))
                elif isinstance(parsed_ev, list):
                    skills_by_comp[comp_id]["evidence_list"].extend(parsed_ev)
                else:
                    skills_by_comp[comp_id]["evidence_list"].append(str(parsed_ev))
            except (json.JSONDecodeError, TypeError):
                skills_by_comp[comp_id]["evidence_list"].append(us.evidence)

    # Compute combined levels: quiz takes priority over profile and self assessments
    result = {}
    for comp_id, data in skills_by_comp.items():
        if "quiz" in data["source_levels"]:
            final_level = float(data["source_levels"]["quiz"])
        else:
            levels = list(data["source_levels"].values())
            final_level = sum(levels) / len(levels) if levels else 0.0

        result[comp_id] = {
            "competency_id": comp_id,
            "competency_name": data["competency_name"],
            "level": round(final_level, 2),
            "sources": sorted(list(set(data["sources"]))),
            "source_breakdown": data["source_levels"],
            "evidence": data["evidence_list"]
        }

    return result


def analyze_role_gap(user_id: int, role_id: int) -> dict:
    """
    Perform competency gap analysis for a user against a target role:
      - For each required competency: gap = max(0, required - current); missing = 0
      - Priority = gap weighted by number of other required competencies that depend on it
      - Flag gaps where an unmet prerequisite blocks learning
      - Overall readiness percentage based on required vs achieved proficiency
    """
    role = db.session.get(Role, role_id)
    if not role:
        return None

    user_skills = get_user_combined_skills(user_id)
    role_competencies = RoleCompetency.query.filter_by(role_id=role_id).all()

    if not role_competencies:
        return {
            "role": role.to_dict(),
            "readiness_percentage": 100.0,
            "competencies": []
        }

    # Map of required competencies for this role: {comp_id: required_level}
    required_map = {rc.competency_id: rc.required_level for rc in role_competencies}
    comp_map = {rc.competency_id: rc.competency for rc in role_competencies}

    # Pre-calculate dependency count: how many OTHER required competencies in this role depend on competency C
    dep_counts = {}
    for comp_id in required_map.keys():
        # Find prerequisites where this competency is the required prerequisite
        dependents = Prerequisite.query.filter_by(requires_competency_id=comp_id).all()
        # Count only dependents that are required for this specific role
        count = sum(1 for d in dependents if d.competency_id in required_map)
        dep_counts[comp_id] = count

    gap_items = []
    total_required = 0.0
    total_achieved = 0.0

    # First pass: collect baseline gaps and current levels
    comp_gap_lookup = {}
    for comp_id, req_level in required_map.items():
        comp = comp_map[comp_id]
        user_skill = user_skills.get(comp_id)

        current_level = float(user_skill["level"]) if user_skill else 0.0
        gap = max(0.0, float(req_level) - current_level)
        comp_gap_lookup[comp_id] = {
            "current": current_level,
            "gap": gap,
            "required": float(req_level)
        }

        total_required += float(req_level)
        total_achieved += min(current_level, float(req_level))

    # Second pass: check prerequisite blocking and priority
    for comp_id, req_level in required_map.items():
        comp = comp_map[comp_id]
        user_skill = user_skills.get(comp_id)

        current_level = comp_gap_lookup[comp_id]["current"]
        gap = comp_gap_lookup[comp_id]["gap"]

        # Priority calculation: gap * (1 + dependents_in_role)
        dep_weight = 1 + dep_counts.get(comp_id, 0)
        priority = round(gap * dep_weight, 2)

        # Check for unmet prerequisites blocking this competency
        prereqs = Prerequisite.query.filter_by(competency_id=comp_id).all()
        blocked_by = []
        is_blocked = False

        if gap > 0:
            for p in prereqs:
                req_comp_id = p.requires_competency_id
                # Check if the prerequisite is unmet (either missing or below required level)
                p_current = comp_gap_lookup.get(req_comp_id, {}).get("current")
                if p_current is None:
                    # Not in role: check user general skill
                    p_skill = user_skills.get(req_comp_id)
                    p_current = float(p_skill["level"]) if p_skill else 0.0

                # Prerequisite is unmet if current level is 0 or less than required
                p_required = required_map.get(req_comp_id, 1.0)
                if p_current < p_required:
                    is_blocked = True
                    blocked_by.append({
                        "competency_id": req_comp_id,
                        "name": p.requires_competency.name if p.requires_competency else f"Competency {req_comp_id}",
                        "current_level": p_current,
                        "required_level": p_required
                    })

        gap_items.append({
            "competency_id": comp.id,
            "name": comp.name,
            "description": comp.description,
            "required_level": req_level,
            "current_level": current_level,
            "gap": round(gap, 2),
            "priority": priority,
            "is_blocked": is_blocked,
            "blocked_by": blocked_by,
            "sources": user_skill["sources"] if user_skill else [],
            "evidence": user_skill["evidence"] if user_skill else []
        })

    # Sort: highest priority first, then highest gap, then name
    gap_items.sort(key=lambda x: (x["priority"], x["gap"], -len(x["name"])), reverse=True)

    readiness_percentage = round((total_achieved / total_required) * 100, 1) if total_required > 0 else 100.0

    return {
        "role": role.to_dict(),
        "readiness_percentage": readiness_percentage,
        "total_required": total_required,
        "total_achieved": round(total_achieved, 2),
        "competencies": gap_items
    }
