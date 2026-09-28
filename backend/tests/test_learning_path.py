import pytest
from backend.app.extensions import db
from backend.app.models.competency import Role, Competency, RoleCompetency, Prerequisite
from backend.app.models.learning import Course, UserCourseProgress
from backend.services.embedder import set_embedder, reset_embedder, FakeEmbedder
from backend.services.course_retriever import find_courses, rebuild_course_index
from backend.services.path_planner import generate_learning_path
from backend.seed import seed_database


@pytest.fixture(autouse=True)
def use_fake_embedder():
    """Ensure FakeEmbedder is used for all tests (no model downloads)."""
    set_embedder(FakeEmbedder())
    yield
    reset_embedder()


# ==========================================
# 1. Course Filtering by Level Range Tests
# ==========================================

def test_course_filtering_by_level_range(app):
    """find_courses filters courses strictly by current_level < level <= target_level."""
    with app.app_context():
        seed_database(app)
        rebuild_course_index()

        comp = Competency.query.filter_by(name="Statistics Fundamentals").first()
        # Seeded courses for Stats Fundamentals: Level 1, Level 3, Level 5
        # If current = 0, target = 3: should return Level 1 and Level 3, but NOT Level 5
        courses = find_courses(
            competency_id=comp.id,
            target_level=3.0,
            current_level=0.0,
            top_k=3
        )
        assert len(courses) > 0
        for c in courses:
            assert c["level"] <= 3
            assert c["level"] > 0

        # If current = 2.0, target = 4.0: should return Level 3 course, NOT Level 1 or 5
        courses_mid = find_courses(
            competency_id=comp.id,
            target_level=4.0,
            current_level=2.0,
            top_k=3
        )
        for c in courses_mid:
            assert 2.0 < c["level"] <= 4.0


# ==========================================
# 2. Topological Ordering & Unmet Prerequisite Pull-in
# ==========================================

def test_topological_ordering_respects_prerequisites(app, client, learner_token, learner_user):
    """
    Topological sort ensures foundational prerequisites are ordered strictly
    before any dependent competencies.
    """
    with app.app_context():
        seed_database(app)
        rebuild_course_index()
        role = Role.query.filter_by(name="Statistical Officer").first()
        role_id = role.id

    headers = {"Authorization": f"Bearer {learner_token}"}
    res = client.get(f"/api/path?role_id={role_id}", headers=headers)
    assert res.status_code == 200
    data = res.get_json()

    assert data["total_steps"] > 0
    step_comp_names = [s["competency_name"] for s in data["steps"]]

    # In seed data: Statistics Fundamentals is prerequisite for Sampling Methods and Regression
    stats_idx = step_comp_names.index("Statistics Fundamentals")
    sampling_idx = step_comp_names.index("Sampling Methods")
    regression_idx = step_comp_names.index("Regression and Forecasting")

    assert stats_idx < sampling_idx, "Statistics Fundamentals must come before Sampling Methods"
    assert stats_idx < regression_idx, "Statistics Fundamentals must come before Regression and Forecasting"

    # Python for Data Analysis is prerequisite for Machine Learning Basics
    python_idx = step_comp_names.index("Python for Data Analysis")
    ml_idx = step_comp_names.index("Machine Learning Basics")
    assert python_idx < ml_idx, "Python must come before Machine Learning Basics"

    # Check stage grouping
    assert len(data["stages"]["Foundation"]) > 0
    assert len(data["stages"]["Core"]) > 0


def test_unmet_prerequisite_pulled_in(app, client, learner_token, learner_user):
    """
    If a role requires competency B, and B requires A, but A is NOT in the role's
    required competencies, A must still be pulled into the learning path.
    """
    with app.app_context():
        seed_database(app)
        rebuild_course_index()

        # Create a custom role that ONLY requires Machine Learning Basics
        ml_comp = Competency.query.filter_by(name="Machine Learning Basics").first()

        custom_role = Role(name="Solo ML Role", description="Requires only ML")
        db.session.add(custom_role)
        db.session.flush()

        rc = RoleCompetency(role_id=custom_role.id, competency_id=ml_comp.id, required_level=3)
        db.session.add(rc)
        db.session.commit()
        role_id = custom_role.id

    headers = {"Authorization": f"Bearer {learner_token}"}
    res = client.get(f"/api/path?role_id={role_id}", headers=headers)
    assert res.status_code == 200
    data = res.get_json()

    step_comp_names = [s["competency_name"] for s in data["steps"]]

    # Even though custom_role only required Machine Learning Basics,
    # Python for Data Analysis and Statistics Fundamentals must be pulled in!
    assert "Python for Data Analysis" in step_comp_names
    assert "Machine Learning Basics" in step_comp_names
    assert step_comp_names.index("Python for Data Analysis") < step_comp_names.index("Machine Learning Basics")


# ==========================================
# 3. Tie-Breaking Order Tests
# ==========================================

def test_topological_sort_tie_breaking(app):
    """
    When multiple nodes have in-degree 0:
    Ties are broken by priority descending, then by smaller gap ascending.
    """
    with app.app_context():
        # Role with 2 independent root competencies
        c1 = Competency(name="Comp High Priority", description="Desc")
        c2 = Competency(name="Comp Low Priority", description="Desc")
        # c3 depends on c1, boosting c1's priority
        c3 = Competency(name="Comp Child", description="Desc")
        db.session.add_all([c1, c2, c3])
        db.session.flush()

        prereq = Prerequisite(competency_id=c3.id, requires_competency_id=c1.id, validate_cycle=False)
        db.session.add(prereq)

        test_role = Role(name="TieBreak Role")
        db.session.add(test_role)
        db.session.flush()

        # c1 gap = 3, dependents = 1 -> priority = 3 * (1 + 1) = 6
        rc1 = RoleCompetency(role_id=test_role.id, competency_id=c1.id, required_level=3)
        # c2 gap = 3, dependents = 0 -> priority = 3 * 1 = 3
        rc2 = RoleCompetency(role_id=test_role.id, competency_id=c2.id, required_level=3)
        # c3 gap = 2
        rc3 = RoleCompetency(role_id=test_role.id, competency_id=c3.id, required_level=2)
        db.session.add_all([rc1, rc2, rc3])
        db.session.commit()

        # Create dummy user
        from backend.app.models.user import User
        user = User(name="TB User", email="tb@test.com", password="password123")
        db.session.add(user)
        db.session.commit()

        path = generate_learning_path(user_id=user.id, role_id=test_role.id)
        step_names = [s["competency_name"] for s in path["steps"]]

        # Both c1 and c2 have in-degree 0 initially, but c1 has priority 6 vs c2 priority 3
        assert step_names.index("Comp High Priority") < step_names.index("Comp Low Priority")


# ==========================================
# 4. Completed Courses Excluded & Empty Path
# ==========================================

def test_completed_courses_excluded_from_path(app, client, learner_token, learner_user):
    """Completed courses are excluded from subsequent path recommendations."""
    with app.app_context():
        seed_database(app)
        rebuild_course_index()
        role = Role.query.filter_by(name="Statistical Assistant").first()
        role_id = role.id

    headers = {"Authorization": f"Bearer {learner_token}"}

    # Step 1: Fetch initial path
    res1 = client.get(f"/api/path?role_id={role_id}", headers=headers)
    assert res1.status_code == 200
    first_step = res1.get_json()["steps"][0]
    assert len(first_step["courses"]) > 0
    first_course = first_step["courses"][0]
    first_course_id = first_course["id"]

    # Step 2: Mark first course as completed
    res_prog = client.post(
        "/api/path/progress",
        json={"course_id": first_course_id, "status": "completed"},
        headers=headers
    )
    assert res_prog.status_code == 200

    # Verify progress GET
    res_get_prog = client.get("/api/path/progress", headers=headers)
    assert res_get_prog.status_code == 200
    assert any(p["course_id"] == first_course_id and p["status"] == "completed" for p in res_get_prog.get_json()["progress"])

    # Step 3: Fetch path again - first_course_id must no longer appear
    res2 = client.get(f"/api/path?role_id={role_id}", headers=headers)
    assert res2.status_code == 200
    updated_steps = res2.get_json()["steps"]
    all_recommended_course_ids = [
        c["id"] for s in updated_steps for c in s["courses"]
    ]
    assert first_course_id not in all_recommended_course_ids


def test_empty_path_when_no_gaps(app, client, learner_token, learner_user):
    """When all competencies meet or exceed required levels, path is empty with completion message."""
    with app.app_context():
        seed_database(app)
        role = Role.query.filter_by(name="Statistical Assistant").first()
        role_id = role.id
        role_comps = RoleCompetency.query.filter_by(role_id=role_id).all()

        # Set self-assessment equal to required level for all role competencies
        self_payload = {rc.competency_id: rc.required_level for rc in role_comps}

    headers = {"Authorization": f"Bearer {learner_token}"}
    client.put("/api/profile/self-assessment", json=self_payload, headers=headers)

    res = client.get(f"/api/path?role_id={role_id}", headers=headers)
    assert res.status_code == 200
    data = res.get_json()

    assert data["total_steps"] == 0
    assert data["steps"] == []
    assert data["readiness_percentage"] == 100.0
    assert "congratulations" in data["message"].lower()


# ==========================================
# 5. Permission & Error Handling Tests
# ==========================================

def test_path_permissions_and_validation(client, learner_token):
    """Test endpoint auth and parameter validation."""
    # Unauthenticated -> 401
    assert client.get("/api/path?role_id=1").status_code == 401
    assert client.post("/api/path/progress", json={"course_id": 1, "status": "completed"}).status_code == 401
    assert client.get("/api/path/progress").status_code == 401

    headers = {"Authorization": f"Bearer {learner_token}"}

    # Missing role_id -> 400
    assert client.get("/api/path", headers=headers).status_code == 400

    # Invalid role_id type -> 400
    assert client.get("/api/path?role_id=abc", headers=headers).status_code == 400

    # Non-existent role -> 404
    assert client.get("/api/path?role_id=99999", headers=headers).status_code == 404

    # Invalid status in progress -> 400
    assert client.post("/api/path/progress", json={"course_id": 1, "status": "finished"}, headers=headers).status_code == 400

    # Non-existent course in progress -> 404
    assert client.post("/api/path/progress", json={"course_id": 99999, "status": "completed"}, headers=headers).status_code == 404
