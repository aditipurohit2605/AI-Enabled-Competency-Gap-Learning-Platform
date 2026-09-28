import networkx as nx
from backend.app.extensions import db
from backend.app.models.competency import Role, Competency, Prerequisite, UserSkill
from backend.app.models.learning import UserCourseProgress
from backend.services.gap import analyze_role_gap, get_user_combined_skills
from backend.services.course_retriever import find_courses


def generate_learning_path(user_id: int, role_id: int) -> dict:
    """
    Generate an optimal, personalized learning path for a learner and target role:
      - Uses gap analysis from Step 3
      - Incorporates unmet prerequisite competencies (even if not explicitly in role)
      - Performs topological sort with tie-breaking: priority descending, then smaller gap
      - Recommends 1 to 3 level-appropriate courses per step (excluding completed courses)
      - Computes data-driven 'why' explanations
      - Groups steps into stages (Foundation, Core, Advanced) by dependency depth
    """
    role = db.session.get(Role, role_id)
    if not role:
        return None

    # Step 1: Run baseline gap analysis
    gap_result = analyze_role_gap(user_id=user_id, role_id=role_id)
    if not gap_result:
        return None

    # Get set of courses the user has already completed
    completed_records = UserCourseProgress.query.filter_by(
        user_id=user_id,
        status="completed"
    ).all()
    completed_course_ids = {r.course_id for r in completed_records}

    user_skills = get_user_combined_skills(user_id)

    # Step 2: Identify competencies with gaps
    # Dict: comp_id -> metadata
    path_competencies = {}
    for item in gap_result["competencies"]:
        if item["gap"] > 0:
            path_competencies[item["competency_id"]] = {
                "competency_id": item["competency_id"],
                "name": item["name"],
                "description": item["description"],
                "current_level": item["current_level"],
                "target_level": item["required_level"],
                "gap": item["gap"],
                "priority": item["priority"],
                "is_in_role": True,
                "is_blocked": item["is_blocked"],
                "blocked_by": item["blocked_by"]
            }

    # Step 3: Pull in unmet prerequisites even if not required by the role
    # Iterate over competencies in path and check their prerequisites
    prereqs_to_check = list(path_competencies.keys())
    visited = set(prereqs_to_check)

    while prereqs_to_check:
        comp_id = prereqs_to_check.pop(0)
        prereqs = Prerequisite.query.filter_by(competency_id=comp_id).all()
        for p in prereqs:
            req_id = p.requires_competency_id
            if req_id not in path_competencies:
                # Check user's current level in this prerequisite
                u_skill = user_skills.get(req_id)
                current_p_level = float(u_skill["level"]) if u_skill else 0.0
                # If learner has level 0 or below minimum prerequisite proficiency (e.g. 2.0)
                if current_p_level < 2.0:
                    req_comp = p.requires_competency
                    if req_comp:
                        p_gap = max(0.0, 2.0 - current_p_level)
                        path_competencies[req_id] = {
                            "competency_id": req_id,
                            "name": req_comp.name,
                            "description": req_comp.description,
                            "current_level": current_p_level,
                            "target_level": 2.0,
                            "gap": p_gap,
                            "priority": round(p_gap * 3.0, 2),  # High priority because it's a blocker
                            "is_in_role": False,
                            "is_blocked": False,
                            "blocked_by": []
                        }
                        if req_id not in visited:
                            visited.add(req_id)
                            prereqs_to_check.append(req_id)

    # If no competency gaps exist, return empty path with completion message
    if not path_competencies:
        return {
            "role": role.to_dict(),
            "total_hours": 0.0,
            "total_steps": 0,
            "readiness_percentage": gap_result["readiness_percentage"],
            "stages": {"Foundation": [], "Core": [], "Advanced": []},
            "steps": [],
            "message": "Congratulations! You have satisfied all competency requirements for this role. No further courses required."
        }

    # Step 4: Build Dependency Graph (NetworkX DiGraph)
    # Edge (u, v) means u is a prerequisite for v (u must be completed before v)
    G = nx.DiGraph()
    for comp_id in path_competencies.keys():
        G.add_node(comp_id)

    for comp_id in path_competencies.keys():
        prereqs = Prerequisite.query.filter_by(competency_id=comp_id).all()
        for p in prereqs:
            if p.requires_competency_id in path_competencies:
                G.add_edge(p.requires_competency_id, comp_id)

    # Step 5: Calculate Dependency Depths for Stage Grouping
    # Depth 0: Foundation, Depth 1: Core, Depth >= 2: Advanced
    depths = {}
    for node in G.nodes():
        # Longest path from any root (in_degree == 0) to this node
        ancestors = nx.ancestors(G, node)
        if not ancestors:
            depths[node] = 0
        else:
            # Subgraph of ancestors + node
            sub = G.subgraph(ancestors | {node})
            try:
                depths[node] = nx.dag_longest_path_length(sub)
            except Exception:
                depths[node] = 1

    # Step 6: Priority-Based Topological Sort (Deterministic Kahn's algorithm)
    # Tie-breaking: Highest priority first, then smaller gap first, then name
    in_degrees = {node: G.in_degree(node) for node in G.nodes()}
    ready_nodes = [node for node, deg in in_degrees.items() if deg == 0]

    def sort_key(node_id):
        item = path_competencies[node_id]
        # Priority descending (negative for min-sort), then gap ascending, then name
        return (-item["priority"], item["gap"], item["name"])

    ordered_comp_ids = []
    while ready_nodes:
        ready_nodes.sort(key=sort_key)
        curr = ready_nodes.pop(0)
        ordered_comp_ids.append(curr)

        for neighbor in G.successors(curr):
            in_degrees[neighbor] -= 1
            if in_degrees[neighbor] == 0:
                ready_nodes.append(neighbor)

    # Step 7: Build Step Details, Courses, and 'Why' Explanations
    steps = []
    stages = {"Foundation": [], "Core": [], "Advanced": []}
    total_hours = 0.0

    for step_num, comp_id in enumerate(ordered_comp_ids, start=1):
        item = path_competencies[comp_id]
        depth = depths.get(comp_id, 0)
        if depth == 0:
            stage_name = "Foundation"
        elif depth == 1:
            stage_name = "Core"
        else:
            stage_name = "Advanced"

        # Find level-appropriate courses (excluding completed ones)
        courses = find_courses(
            competency_id=comp_id,
            target_level=item["target_level"],
            current_level=item["current_level"],
            top_k=3,
            exclude_course_ids=completed_course_ids
        )

        step_hours = sum(c.get("duration_hours", 5.0) for c in courses)
        total_hours += step_hours

        # Generate data-driven 'why' explanation
        dependents_in_path = [
            path_competencies[succ]["name"]
            for succ in G.successors(comp_id)
        ]

        if not item["is_in_role"]:
            why = (
                f"Essential prerequisite skill required before learning "
                f"{', '.join(dependents_in_path) if dependents_in_path else 'downstream competencies'} "
                f"(Current Level: {item['current_level']:.1f}, Target: {item['target_level']:.1f})."
            )
        elif dependents_in_path:
            why = (
                f"High-priority foundational competency (Priority: {item['priority']:.1f}, Gap: {item['gap']:.1f}) "
                f"that unlocks {len(dependents_in_path)} downstream required skill(s): {', '.join(dependents_in_path)}."
            )
        elif item["is_blocked"]:
            blocker_names = [b["name"] for b in item["blocked_by"]]
            why = (
                f"Required competency with a gap of {item['gap']:.1f} levels, "
                f"scheduled after prerequisites ({', '.join(blocker_names)}) are completed."
            )
        else:
            why = (
                f"Closes key competency gap of {item['gap']:.1f} levels to meet "
                f"{role.name} proficiency standard (Target Level: {item['target_level']:.1f})."
            )

        step_dict = {
            "step_number": step_num,
            "competency_id": comp_id,
            "competency_name": item["name"],
            "stage": stage_name,
            "dependency_depth": depth,
            "current_level": item["current_level"],
            "target_level": item["target_level"],
            "gap": item["gap"],
            "priority": item["priority"],
            "why": why,
            "courses": courses,
            "estimated_hours": round(step_hours, 1)
        }

        steps.append(step_dict)
        stages[stage_name].append({
            "step_number": step_num,
            "competency_name": item["name"],
            "courses_count": len(courses)
        })

    return {
        "role": role.to_dict(),
        "total_hours": round(total_hours, 1),
        "total_steps": len(steps),
        "readiness_percentage": gap_result["readiness_percentage"],
        "stages": stages,
        "steps": steps
    }
