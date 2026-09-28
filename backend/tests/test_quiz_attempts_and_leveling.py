import io
import pytest

from backend.app.extensions import db
from backend.app.models.assessment import Document, Question, QuizAttempt, QuizSession, GapSnapshot
from backend.app.models.competency import Role, Competency, RoleCompetency, UserSkill
from backend.app.models.user import User
from backend.app.utils.auth import generate_token
from backend.services.embedder import set_embedder, reset_embedder, FakeEmbedder
from backend.services.llm_client import set_llm_client, reset_llm_client, FakeLLMClient
from backend.services.leveling import (
    determine_quiz_level,
    blend_competency_level,
    calculate_quiz_score_and_weights
)
from backend.services.gap import analyze_role_gap, get_user_combined_skills


@pytest.fixture(autouse=True)
def setup_services():
    set_embedder(FakeEmbedder())
    set_llm_client(FakeLLMClient())
    yield
    reset_embedder()
    reset_llm_client()


@pytest.fixture
def test_setup_data(app):
    """Seed role, competencies, documents, and approved questions."""
    with app.app_context():
        role = Role(name="Survey Statistician", description="Designs and conducts surveys")
        db.session.add(role)

        comp1 = Competency(name="Sampling Methods", description="Probability sampling designs")
        comp2 = Competency(name="Survey Design", description="Questionnaire design and pretesting")
        db.session.add_all([comp1, comp2])
        db.session.commit()

        rc1 = RoleCompetency(role_id=role.id, competency_id=comp1.id, required_level=4)
        rc2 = RoleCompetency(role_id=role.id, competency_id=comp2.id, required_level=3)
        db.session.add_all([rc1, rc2])

        doc = Document(title="Sampling Manual", filename="sampling.txt", uploaded_by=1, competency_id=comp1.id)
        db.session.add(doc)
        db.session.commit()

        # Seed 5 approved questions for comp1 (mix of easy, medium, hard)
        q1 = Question(
            text="What is simple random sampling?",
            options=["Equal chance for all", "Quota based", "Convenience", "Subjective"],
            correct_index=0,
            document_id=doc.id,
            explanation="SRS gives equal chance to every unit.",
            source_passage="SRS gives equal chance to every unit.",
            difficulty="easy",
            status="approved"
        )
        q2 = Question(
            text="What is stratified sampling?",
            options=["Division into homogenous strata", "Selecting only clusters", "Purposive", "Volunteer pool"],
            correct_index=0,
            document_id=doc.id,
            explanation="Stratified sampling divides into strata.",
            source_passage="Stratified sampling divides into strata.",
            difficulty="medium",
            status="approved"
        )
        q3 = Question(
            text="What is cluster sampling?",
            options=["Selecting primary sampling units", "Complete enumeration", "Non-probability selection", "Haphazard"],
            correct_index=0,
            document_id=doc.id,
            explanation="Cluster sampling selects PSUs.",
            source_passage="Cluster sampling selects PSUs.",
            difficulty="medium",
            status="approved"
        )
        q4 = Question(
            text="What is PPS sampling?",
            options=["Probability proportional to size", "Purely purposive sample", "Pilot sample size", "Post-stratified size"],
            correct_index=0,
            document_id=doc.id,
            explanation="PPS is probability proportional to size.",
            source_passage="PPS is probability proportional to size.",
            difficulty="hard",
            status="approved"
        )
        q5 = Question(
            text="What is a design effect (Deff)?",
            options=["Ratio of variance under complex design to SRS", "Difference in sample sizes", "Response rate metric", "Cost ratio"],
            correct_index=0,
            document_id=doc.id,
            explanation="Deff is the ratio of variances.",
            source_passage="Deff is the ratio of variances.",
            difficulty="hard",
            status="approved"
        )
        db.session.add_all([q1, q2, q3, q4, q5])
        db.session.commit()

        return {
            "role_id": role.id,
            "comp1_id": comp1.id,
            "comp2_id": comp2.id,
            "question_ids": [q1.id, q2.id, q3.id, q4.id, q5.id]
        }


# -------------------------------------------------------------
# 1. Leveling Math & Boundary Tests
# -------------------------------------------------------------

def test_leveling_boundaries():
    """Verify exact score percentage thresholds: 39, 40, 59, 60, 74, 75, 89, 90."""
    assert determine_quiz_level(39.0, total_questions=5, hard_correct_count=1) == 1
    assert determine_quiz_level(40.0, total_questions=5, hard_correct_count=1) == 2
    assert determine_quiz_level(59.9, total_questions=5, hard_correct_count=1) == 2
    assert determine_quiz_level(60.0, total_questions=5, hard_correct_count=1) == 3
    assert determine_quiz_level(74.9, total_questions=5, hard_correct_count=1) == 3
    assert determine_quiz_level(75.0, total_questions=5, hard_correct_count=1) == 4
    assert determine_quiz_level(89.9, total_questions=5, hard_correct_count=1) == 4
    assert determine_quiz_level(90.0, total_questions=5, hard_correct_count=1) == 5


def test_level_5_requirements():
    """Level 5 requires score >= 90%, at least 5 questions, and at least 1 hard correct question."""
    # Score 95% with 5 questions and 1 hard correct -> Level 5
    assert determine_quiz_level(95.0, total_questions=5, hard_correct_count=1) == 5

    # Score 95% but zero hard questions correct -> capped at Level 4
    assert determine_quiz_level(95.0, total_questions=5, hard_correct_count=0) == 4

    # Score 100% with only 4 questions -> capped at Level 4
    assert determine_quiz_level(100.0, total_questions=4, hard_correct_count=1) == 4


def test_drop_cap_of_one_level():
    """Level blend must never drop more than 1 level in a single session."""
    # Previous level was 4.0, quiz level was 1
    # 70% quiz (1) + 30% prev (4) = 0.7 + 1.2 = 1.9 -> round(1.9) = 2.0
    # But drop cap prevents dropping below 4.0 - 1.0 = 3.0
    new_lvl = blend_competency_level(quiz_level=1, previous_level=4.0, total_questions=5)
    assert new_lvl == 3.0

    # Previous level was 5.0, quiz level was 1
    new_lvl5 = blend_competency_level(quiz_level=1, previous_level=5.0, total_questions=5)
    assert new_lvl5 == 4.0


def test_half_weight_for_small_sessions():
    """Sessions with fewer than 5 questions count at half weight (40/60 blend)."""
    # 3 questions session: 40% quiz (5) + 60% prev (2.0) = 2.0 + 1.2 = 3.2 -> 3.0
    new_lvl = blend_competency_level(quiz_level=5, previous_level=2.0, total_questions=3)
    assert new_lvl == 3.0

    # Compare with 5 questions: 70% quiz (5) + 30% prev (2.0) = 3.5 + 0.6 = 4.1 -> 4.0
    normal_lvl = blend_competency_level(quiz_level=5, previous_level=2.0, total_questions=5)
    assert normal_lvl == 4.0


# -------------------------------------------------------------
# 2. Session Lifecycle & Double-Submit Safety Tests
# -------------------------------------------------------------

def test_start_and_submit_quiz_flow(client, learner_token, test_setup_data):
    """Start session, submit answers, and receive score with updated level."""
    comp_id = test_setup_data["comp1_id"]
    role_id = test_setup_data["role_id"]

    # 1. Start quiz session
    start_res = client.post(
        f"/api/quiz/{comp_id}/start",
        json={"n": 5},
        headers={"Authorization": f"Bearer {learner_token}"}
    )
    assert start_res.status_code == 201
    data = start_res.get_json()
    session_id = data["session_id"]
    questions = data["questions"]
    assert len(questions) == 5

    # Verify answers are NOT returned before submit
    for q in questions:
        assert "correct_index" not in q
        assert "explanation" not in q

    # 2. Submit answers (answer all correctly)
    answers = {q["id"]: 0 for q in questions}
    sub_res = client.post(
        f"/api/quiz/session/{session_id}/submit",
        json={"answers": answers, "role_id": role_id},
        headers={"Authorization": f"Bearer {learner_token}"}
    )
    assert sub_res.status_code == 200
    res_data = sub_res.get_json()["result"]
    assert res_data["score_pct"] == 100.0
    assert res_data["new_level"] == 5.0
    assert res_data["gap_snapshot"] is not None

    # Verify explanations ARE returned after submit
    for q_res in res_data["question_results"]:
        assert "correct_index" in q_res
        assert "explanation" in q_res
        assert q_res["is_correct"] is True

    # 3. Double-submit safety: second call must return saved result without error or duplicating attempts
    sub_res_2 = client.post(
        f"/api/quiz/session/{session_id}/submit",
        json={"answers": answers},
        headers={"Authorization": f"Bearer {learner_token}"}
    )
    assert sub_res_2.status_code == 200
    assert "already submitted" in sub_res_2.get_json()["message"]
    assert sub_res_2.get_json()["score_pct"] == 100.0

    # Ensure attempts were not duplicated
    attempts = QuizAttempt.query.filter_by(session_id=session_id).all()
    assert len(attempts) == 5


def test_cross_user_submission_forbidden(client, learner_token, trainer_token, test_setup_data):
    """Another user cannot submit my quiz session."""
    comp_id = test_setup_data["comp1_id"]

    # Learner starts session
    start_res = client.post(
        f"/api/quiz/{comp_id}/start",
        json={"n": 3},
        headers={"Authorization": f"Bearer {learner_token}"}
    )
    session_id = start_res.get_json()["session_id"]

    # Trainer attempts to submit learner's session
    cross_res = client.post(
        f"/api/quiz/session/{session_id}/submit",
        json={"answers": {}},
        headers={"Authorization": f"Bearer {trainer_token}"}
    )
    assert cross_res.status_code == 403
    assert "cannot submit another user" in cross_res.get_json()["message"].lower()


def test_quiz_history_and_gap_trend(client, learner_token, test_setup_data):
    """User can view submitted quiz history and GapSnapshot trend over time."""
    comp_id = test_setup_data["comp1_id"]
    role_id = test_setup_data["role_id"]

    # Start and submit a session
    start_res = client.post(
        f"/api/quiz/{comp_id}/start",
        json={"n": 3},
        headers={"Authorization": f"Bearer {learner_token}"}
    )
    session_id = start_res.get_json()["session_id"]
    client.post(
        f"/api/quiz/session/{session_id}/submit",
        json={"answers": {}, "role_id": role_id},
        headers={"Authorization": f"Bearer {learner_token}"}
    )

    # 1. History
    hist_res = client.get("/api/quiz/history", headers={"Authorization": f"Bearer {learner_token}"})
    assert hist_res.status_code == 200
    history = hist_res.get_json()["history"]
    assert len(history) >= 1
    assert history[0]["id"] == session_id

    # 2. Gap Trend
    trend_res = client.get(
        f"/api/progress/gap-trend?role_id={role_id}",
        headers={"Authorization": f"Bearer {learner_token}"}
    )
    assert trend_res.status_code == 200
    snapshots = trend_res.get_json()["snapshots"]
    assert len(snapshots) >= 1
    assert "readiness_pct" in snapshots[0]


# -------------------------------------------------------------
# 3. Skill Merge Priority & Gap Integration Tests
# -------------------------------------------------------------

def test_quiz_level_overrides_profile_level_in_gap_service(app, test_setup_data):
    """Quiz result takes priority over profile and self assessments in gap analysis."""
    with app.app_context():
        comp_id = test_setup_data["comp1_id"]
        role_id = test_setup_data["role_id"]

        user = User(name="David Test", email="david@example.com", password="password123", role="learner")
        db.session.add(user)
        db.session.commit()

        # Add profile skill (level 1.0) and self assessment skill (level 2.0)
        s1 = UserSkill(user_id=user.id, competency_id=comp_id, level=1.0, source="profile", evidence="Profile text")
        s2 = UserSkill(user_id=user.id, competency_id=comp_id, level=2.0, source="self", evidence="Self rated")
        db.session.add_all([s1, s2])
        db.session.commit()

        # Before quiz: combined level is average of 1.0 and 2.0 = 1.5
        before = get_user_combined_skills(user.id)
        assert before[comp_id]["level"] == 1.5
        assert set(before[comp_id]["sources"]) == {"profile", "self"}

        # Now add quiz skill (level 4.0)
        s3 = UserSkill(user_id=user.id, competency_id=comp_id, level=4.0, source="quiz", evidence="Quiz result")
        db.session.add(s3)
        db.session.commit()

        # After quiz: combined level MUST be 4.0 (quiz priority)
        after = get_user_combined_skills(user.id)
        assert after[comp_id]["level"] == 4.0
        assert set(after[comp_id]["sources"]) == {"profile", "self", "quiz"}

        # In role gap analysis: current level must be 4.0, gap = 4.0 - 4.0 = 0.0
        gap_analysis = analyze_role_gap(user.id, role_id)
        comp_gap = next(c for c in gap_analysis["competencies"] if c["competency_id"] == comp_id)
        assert comp_gap["current_level"] == 4.0
        assert comp_gap["gap"] == 0.0


# -------------------------------------------------------------
# 4. Diagnostic Mode Tests
# -------------------------------------------------------------

def test_diagnostic_mode_skips_unassessed_competencies(client, learner_token, test_setup_data):
    """
    Diagnostic mode:
    - Builds sessions for competencies with >= 3 questions.
    - Reports competencies with < 3 questions as 'not assessed' (not level 0).
    """
    role_id = test_setup_data["role_id"]
    comp1_id = test_setup_data["comp1_id"]  # Has 5 approved questions
    comp2_id = test_setup_data["comp2_id"]  # Has 0 approved questions

    # 1. Start diagnostic
    diag_start_res = client.post(
        f"/api/diagnostic/start?role_id={role_id}",
        headers={"Authorization": f"Bearer {learner_token}"}
    )
    assert diag_start_res.status_code == 200
    diag_data = diag_start_res.get_json()

    # Comp1 should have an active session
    assert len(diag_data["sessions"]) == 1
    session_info = diag_data["sessions"][0]
    assert session_info["competency_id"] == comp1_id
    assert len(session_info["questions"]) == 3

    # Comp2 should be reported as not assessed
    assert len(diag_data["not_assessed"]) == 1
    unassessed = diag_data["not_assessed"][0]
    assert unassessed["competency_id"] == comp2_id
    assert unassessed["status"] == "not assessed"

    # 2. Submit diagnostic
    diag_submit_res = client.post(
        "/api/diagnostic/submit",
        json={
            "role_id": role_id,
            "sessions": [
                {
                    "session_id": session_info["session_id"],
                    "answers": {q["id"]: 0 for q in session_info["questions"]}
                }
            ]
        },
        headers={"Authorization": f"Bearer {learner_token}"}
    )
    assert diag_submit_res.status_code == 200
    sub_data = diag_submit_res.get_json()
    assert len(sub_data["session_results"]) == 1
    assert sub_data["gap_snapshot"] is not None
