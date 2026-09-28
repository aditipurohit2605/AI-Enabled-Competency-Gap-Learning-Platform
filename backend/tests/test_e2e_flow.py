import io
import pytest
from unittest.mock import patch
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.competency import Role, Competency, RoleCompetency
from backend.app.models.learning import Course
from backend.services.llm_client import BaseLLMClient


class MockE2ELLMClient(BaseLLMClient):
    """Deterministic mock LLM client for end-to-end integration test."""

    def generate_json(self, prompt: str, schema=None, timeout=30, max_retries=3, backoff_factor=1.5):
        return {
            "questions": [
                {
                    "question": "What is the primary benefit of stratified random sampling in survey research?",
                    "options": [
                        "It minimizes variance by grouping similar units into homogeneous strata.",
                        "It eliminates the need to compile a sampling frame.",
                        "It guarantees that every stratum will have identical sample size.",
                        "It prevents respondents from declining interviews."
                    ],
                    "correct_index": 0,
                    "explanation": "Homogeneous strata reduce within-group variance, yielding higher estimator precision.",
                    "difficulty": "medium",
                    "source_passage": "Stratified random sampling minimizes estimator variance by creating homogeneous strata."
                },
                {
                    "question": "When is cluster sampling operationalized in official statistics?",
                    "options": [
                        "When population elements are geographically dispersed and travel costs are high.",
                        "When all cluster elements are identical in every attribute.",
                        "When the sampling error must equal zero.",
                        "When simple random sampling without replacement is prohibited."
                    ],
                    "correct_index": 0,
                    "explanation": "Cluster sampling optimizes field logistics and reduces transport costs.",
                    "difficulty": "easy",
                    "source_passage": "Cluster sampling reduces logistics overhead across dispersed geographical regions."
                },
                {
                    "question": "How does probability proportional to size (PPS) sampling select primary units?",
                    "options": [
                        "Units with higher size measures have proportionately greater selection chances.",
                        "Units with smaller populations are selected first.",
                        "All primary units receive equal probability regardless of size.",
                        "Small villages are permanently removed from the universe."
                    ],
                    "correct_index": 0,
                    "explanation": "PPS weights selection odds proportionally to the auxiliary size metric.",
                    "difficulty": "medium",
                    "source_passage": "PPS assigns selection likelihood according to population or enterprise size measures."
                }
            ]
        }


def test_complete_end_to_end_platform_lifecycle(app, client):
    """
    Test complete user and system lifecycle from start to finish:
      1. Register learner
      2. Extract skills from profile bio
      3. Evaluate initial role gap
      4. Inspect learning path recommendations
      5. Trainer uploads reference document
      6. Trainer generates MCQs using mock LLM
      7. Trainer reviews and approves questions
      8. Learner initiates assessment session
      9. Learner submits quiz answers
      10. Verify competency level increases and role gap improves
    """
    # 0. Seed minimal framework
    with app.app_context():
        comp_sampling = Competency(name="Sampling Methods", description="Survey sampling techniques")
        comp_stats = Competency(name="Statistics Fundamentals", description="Probability and inference")
        db.session.add_all([comp_sampling, comp_stats])
        db.session.commit()

        role = Role(name="Field Statistical Officer", description="Conducts field surveys")
        db.session.add(role)
        db.session.commit()

        rc1 = RoleCompetency(role_id=role.id, competency_id=comp_sampling.id, required_level=3)
        rc2 = RoleCompetency(role_id=role.id, competency_id=comp_stats.id, required_level=2)
        db.session.add_all([rc1, rc2])

        course = Course(
            title="Advanced Survey Sampling",
            competency_id=comp_sampling.id,
            level=2,
            duration_hours=12,
            provider="MoSPI Training Division"
        )
        db.session.add(course)
        db.session.commit()

        trainer = User(name="Master Trainer", email="trainer_e2e@example.com", password="pass", role="trainer")
        db.session.add(trainer)
        db.session.commit()

        role_id = role.id
        sampling_comp_id = comp_sampling.id

    # 1. Register learner
    reg_res = client.post("/api/auth/register", json={
        "name": "Sunil Varma",
        "email": "sunil.varma@example.com",
        "password": "securepassword123",
        "role": "learner"
    })
    assert reg_res.status_code == 201
    learner_token = reg_res.get_json()["token"]
    learner_headers = {"Authorization": f"Bearer {learner_token}"}

    # Assign target role
    with app.app_context():
        u = User.query.filter_by(email="sunil.varma@example.com").first()
        u.target_role_id = role_id
        db.session.commit()

    # 2. Extract profile skills
    profile_bio = "Field investigator with 3 years executing basic surveys. Strong in Statistics Fundamentals and data validation."
    prof_res = client.post("/api/profile/analyze", json={"text": profile_bio}, headers=learner_headers)
    assert prof_res.status_code == 200

    # 3. Initial Role Gap Analysis
    gap_res_1 = client.get(f"/api/gap?role_id={role_id}", headers=learner_headers)
    assert gap_res_1.status_code == 200
    initial_gap_data = gap_res_1.get_json()
    initial_readiness = initial_gap_data["readiness_percentage"]

    # Locate sampling gap
    sampling_gap_entry = next((c for c in initial_gap_data["competencies"] if c["competency_id"] == sampling_comp_id), None)
    assert sampling_gap_entry is not None
    assert sampling_gap_entry["gap"] > 0  # There is an initial gap

    # 4. Learning Path Recommendation
    path_res = client.get(f"/api/path?role_id={role_id}", headers=learner_headers)
    assert path_res.status_code == 200
    path_data = path_res.get_json()
    assert "steps" in path_data

    # 5. Trainer Ingestion
    login_trainer = client.post("/api/auth/login", json={"email": "trainer_e2e@example.com", "password": "pass"})
    assert login_trainer.status_code == 200
    trainer_token = login_trainer.get_json()["token"]
    trainer_headers = {"Authorization": f"Bearer {trainer_token}"}

    doc_text = """
    Sampling Techniques Manual.
    Stratified random sampling minimizes estimator variance by creating homogeneous strata.
    Cluster sampling reduces logistics overhead across dispersed geographical regions.
    PPS assigns selection likelihood according to population or enterprise size measures.
    """
    file_bytes = io.BytesIO(doc_text.strip().encode("utf-8"))
    upload_res = client.post(
        "/api/documents",
        data={
            "file": (file_bytes, "sampling_guide.txt"),
            "title": "Sampling Techniques Guide",
            "competency_id": str(sampling_comp_id)
        },
        content_type="multipart/form-data",
        headers=trainer_headers
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.get_json()["document"]["id"]

    # 6. Generate MCQs using Mocked LLM
    with patch("backend.services.mcq_generator.get_llm_client", return_value=MockE2ELLMClient()):
        gen_res = client.post(
            f"/api/documents/{doc_id}/generate",
            json={"num_questions": 3, "difficulty": "medium"},
            headers=trainer_headers
        )
        assert gen_res.status_code == 200
        assert gen_res.get_json()["result"]["kept"] == 3

    # 7. Trainer Review & Approve All
    approve_res = client.post(f"/api/documents/{doc_id}/approve-all", headers=trainer_headers)
    assert approve_res.status_code == 200
    assert approve_res.get_json()["approved_count"] == 3

    # 8. Learner Quiz Assessment Start
    quiz_start_res = client.post(
        f"/api/quiz/{sampling_comp_id}/start",
        json={"n": 3},
        headers=learner_headers
    )
    assert quiz_start_res.status_code in (200, 201)
    quiz_payload = quiz_start_res.get_json()
    session_id = quiz_payload["session_id"]
    assigned_questions = quiz_payload["questions"]
    assert len(assigned_questions) == 3
    # Verify answers are NOT leaked to learner
    for q in assigned_questions:
        assert "correct_index" not in q
        assert "explanation" not in q

    # 9. Learner Submits Quiz (All Correct)
    # Correct index from our mock generator is 0
    answers = {str(q["id"]): 0 for q in assigned_questions}
    submit_res = client.post(
        f"/api/quiz/session/{session_id}/submit",
        json={"answers": answers},
        headers=learner_headers
    )
    assert submit_res.status_code == 200
    res_body = submit_res.get_json()
    submission_data = res_body.get("result", res_body)
    assert submission_data["score_pct"] == 100.0
    assert submission_data["level_after"] >= submission_data["level_before"]

    # 10. Verify Gap and Readiness Improvement
    gap_res_2 = client.get(f"/api/gap?role_id={role_id}", headers=learner_headers)
    assert gap_res_2.status_code == 200
    updated_gap_data = gap_res_2.get_json()
    updated_readiness = updated_gap_data["readiness_percentage"]

    # Verify learner role readiness improved
    assert updated_readiness >= initial_readiness

    updated_sampling_entry = next((c for c in updated_gap_data["competencies"] if c["competency_id"] == sampling_comp_id), None)
    assert updated_sampling_entry is not None
    assert updated_sampling_entry["current_level"] > sampling_gap_entry["current_level"]
    assert updated_sampling_entry["gap"] < sampling_gap_entry["gap"]
