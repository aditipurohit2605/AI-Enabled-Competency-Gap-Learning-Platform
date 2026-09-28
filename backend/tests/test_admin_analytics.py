import datetime
import pytest
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.competency import Role, Competency, RoleCompetency, UserSkill
from backend.app.models.assessment import QuizSession, Document, Question


def test_admin_analytics_permissions(client, learner_token, trainer_token, admin_token):
    # Unauthenticated
    res = client.get("/api/admin/analytics")
    assert res.status_code == 401

    # Learner forbidden
    res = client.get("/api/admin/analytics", headers={"Authorization": f"Bearer {learner_token}"})
    assert res.status_code == 403

    # Trainer forbidden
    res = client.get("/api/admin/analytics", headers={"Authorization": f"Bearer {trainer_token}"})
    assert res.status_code == 403

    # Admin allowed
    res = client.get("/api/admin/analytics", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.get_json()
    assert "num_learners" in data
    assert "average_readiness" in data
    assert "top_gaps" in data
    assert "learner_matrix" in data


def test_admin_users_endpoint(client, learner_token, trainer_token, admin_token):
    # Permissions
    res = client.get("/api/admin/users")
    assert res.status_code == 401

    res = client.get("/api/admin/users", headers={"Authorization": f"Bearer {learner_token}"})
    assert res.status_code == 403

    res = client.get("/api/admin/users", headers={"Authorization": f"Bearer {trainer_token}"})
    assert res.status_code == 403

    res = client.get("/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.get_json()
    assert "users" in data
    assert len(data["users"]) >= 3  # learner, trainer, admin
    roles = {u["role"] for u in data["users"]}
    assert "learner" in roles
    assert "trainer" in roles
    assert "admin" in roles


def test_admin_analytics_aggregation(app, client, admin_token, learner_user):
    """Seed data and test analytics aggregation calculations."""
    with app.app_context():
        # Add a second learner
        learner2 = User(name="David Learner", email="david@example.com", password="pass", role="learner")
        db.session.add(learner2)
        db.session.commit()

        # Add competencies
        c1 = Competency(name="Python Programming", description="Core Python skills")
        c2 = Competency(name="Statistical Modeling", description="Data science and stats")
        c3 = Competency(name="Data Visualization", description="Charts and reporting")
        db.session.add_all([c1, c2, c3])
        db.session.commit()

        # Add Role
        role = Role(name="Data Analyst", description="Analyzes datasets")
        db.session.add(role)
        db.session.commit()

        # Role requirements: c1 -> level 3, c2 -> level 4, c3 -> level 2
        rc1 = RoleCompetency(role_id=role.id, competency_id=c1.id, required_level=3)
        rc2 = RoleCompetency(role_id=role.id, competency_id=c2.id, required_level=4)
        rc3 = RoleCompetency(role_id=role.id, competency_id=c3.id, required_level=2)
        db.session.add_all([rc1, rc2, rc3])

        # Assign user target role to learner 1
        l1 = db.session.get(User, learner_user["id"])
        l1.target_role_id = role.id

        # Seed skills for learner 1: c1 = level 2 (gap 1), c2 = level 2 (gap 2), c3 = level 2 (gap 0)
        s1 = UserSkill(user_id=l1.id, competency_id=c1.id, level=2, source="quiz")
        s2 = UserSkill(user_id=l1.id, competency_id=c2.id, level=2, source="quiz")
        s3 = UserSkill(user_id=l1.id, competency_id=c3.id, level=2, source="quiz")

        # Seed skills for learner 2: c1 = level 1 (gap 2), c2 = level 1 (gap 3), c3 = level 0 (gap 2)
        s4 = UserSkill(user_id=learner2.id, competency_id=c1.id, level=1, source="self_assessed")
        s5 = UserSkill(user_id=learner2.id, competency_id=c2.id, level=1, source="self_assessed")

        db.session.add_all([s1, s2, s3, s4, s5])
        db.session.commit()

        # Seed QuizSessions
        now = datetime.datetime.now(datetime.timezone.utc)
        qs1 = QuizSession(
            user_id=l1.id,
            competency_id=c1.id,
            question_ids=[1, 2],
            started_at=now,
            submitted_at=now,
            score_pct=85.0,
            level_before=1.0,
            level_after=2.0
        )
        qs2 = QuizSession(
            user_id=learner2.id,
            competency_id=c1.id,
            question_ids=[1, 2],
            started_at=now,
            submitted_at=now,
            score_pct=75.0,
            level_before=0.0,
            level_after=1.0
        )
        qs3 = QuizSession(
            user_id=l1.id,
            competency_id=c2.id,
            question_ids=[3, 4],
            started_at=now,
            submitted_at=now,
            score_pct=90.0,
            level_before=1.0,
            level_after=2.0
        )
        db.session.add_all([qs1, qs2, qs3])
        db.session.commit()

        target_role_id = role.id
        c1_id = c1.id
        c2_id = c2.id

    # Call admin analytics with role_id
    res = client.get(f"/api/admin/analytics?role_id={target_role_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.get_json()

    assert data["num_learners"] == 2
    assert data["role_id"] == target_role_id
    assert data["role_name"] == "Data Analyst"
    assert data["total_quizzes_taken"] == 3
    assert data["average_readiness"] > 0

    # Top gaps should contain c2 and c1
    top_gaps = data["top_gaps"]
    assert len(top_gaps) > 0
    comp_names = [g["competency_name"] for g in top_gaps]
    assert "Statistical Modeling" in comp_names
    assert "Python Programming" in comp_names

    # Check matrix
    matrix = data["learner_matrix"]
    assert len(matrix) == 2
    l1_entry = next(item for item in matrix if item["learner_name"] == "Alice Learner")
    assert l1_entry["competencies"][str(c1_id)] == 2.0

    # Check quiz stats by competency
    quiz_stats = data["quiz_stats_by_competency"]
    c1_stat = next(s for s in quiz_stats if s["competency_id"] == c1_id)
    assert c1_stat["quiz_count"] == 2
    assert c1_stat["average_score"] == 80.0  # (85 + 75) / 2


def test_trainer_questions_endpoint(client, trainer_token, learner_token):
    # Learner should be forbidden
    res = client.get("/api/questions", headers={"Authorization": f"Bearer {learner_token}"})
    assert res.status_code == 403

    # Trainer should be allowed
    res = client.get("/api/questions", headers={"Authorization": f"Bearer {trainer_token}"})
    assert res.status_code == 200
    data = res.get_json()
    assert "questions" in data
    assert "count" in data
