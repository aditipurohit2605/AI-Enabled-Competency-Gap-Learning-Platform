from pathlib import Path
import pytest
from backend.app.models.competency import Role, Competency, RoleCompetency, Prerequisite, UserSkill
from backend.services.embedder import set_embedder, reset_embedder, FakeEmbedder, embed
from backend.services.skill_extractor import (
    split_into_sentences,
    estimate_competency_level,
    extract_skills_from_profile
)
from backend.services.gap import analyze_role_gap, get_user_combined_skills
from backend.seed import seed_database


@pytest.fixture(autouse=True)
def use_fake_embedder():
    """Ensure FakeEmbedder is always used for tests (no model downloads)."""
    set_embedder(FakeEmbedder())
    yield
    reset_embedder()


# ==========================================
# 1. Embedder & Level Rules Tests
# ==========================================

def test_fake_embedder_returns_normalized_vectors():
    """FakeEmbedder must return unit-normalized vectors without downloading models."""
    vectors = embed(["Statistics Fundamentals", "Data Cleaning with SQL"])
    assert vectors.shape[0] == 2
    assert vectors.shape[1] == 1024
    import numpy as np
    norm0 = np.linalg.norm(vectors[0])
    norm1 = np.linalg.norm(vectors[1])
    assert abs(norm0 - 1.0) < 1e-4
    assert abs(norm1 - 1.0) < 1e-4


def test_sentence_splitting():
    """Text is cleanly split into sentences while filtering noise."""
    text = (
        "Statistical Officer Profile.\n"
        "• Conducted 10 field surveys using stratified sampling.\n"
        "- Cleaned survey datasets using SQL. Implemented validation routines in Python!"
    )
    sentences = split_into_sentences(text)
    assert len(sentences) >= 3
    assert any("stratified sampling" in s for s in sentences)
    assert any("SQL" in s for s in sentences)


def test_level_estimation_rules():
    """
    Transparent level rules (1-4 only; capped at 4):
      - Base: 1 for mention
      - +1 for years of experience
      - +1 for concrete tool or project
      - +1 for certification or course
    """
    # 1. Mention only -> Level 1
    lvl1, r1 = estimate_competency_level(["Understands survey design principles."])
    assert lvl1 == 1
    assert len(r1) == 1

    # 2. Mention + years of experience -> Level 2
    lvl2, r2 = estimate_competency_level(["Has 4 years of experience conducting survey sampling."])
    assert lvl2 == 2
    assert any("experience" in r.lower() for r in r2)

    # 3. Mention + years of experience + concrete tool/project -> Level 3
    lvl3, r3 = estimate_competency_level([
        "Has 4 years of experience conducting survey sampling.",
        "Built automated data cleaning pipeline using SQL and Python."
    ])
    assert lvl3 == 3
    assert any("tools" in r.lower() or "projects" in r.lower() for r in r3)

    # 4. Mention + experience + tool + certification -> Level 4
    lvl4, r4 = estimate_competency_level([
        "Has 4 years of experience conducting survey sampling.",
        "Built automated data cleaning pipeline using SQL.",
        "Completed iGOT Karmayogi certified training on sampling techniques."
    ])
    assert lvl4 == 4
    assert any("certification" in r.lower() or "training" in r.lower() for r in r4)

    # 5. Cap test: even with multiple certifications and projects, level never exceeds 4
    lvl_cap, _ = estimate_competency_level([
        "10 years of experience managing statistical pipelines.",
        "Built enterprise databases using PostgreSQL, Docker, Git, and Python.",
        "Holds Master degree and certified by iGOT Karmayogi accreditation program.",
        "Led multiple national survey projects."
    ])
    assert lvl_cap == 4


# ==========================================
# 2. Extraction on Sample Profile Text
# ==========================================

def test_extract_skills_from_sample_profile(app):
    """Extract skills from the sample profile_officer.txt file."""
    sample_path = Path(__file__).resolve().parent.parent / "samples" / "profile_officer.txt"
    assert sample_path.exists(), f"Sample file not found at {sample_path}"
    profile_text = sample_path.read_text(encoding="utf-8")

    with app.app_context():
        seed_database(app)
        competencies = Competency.query.all()
        # Lower threshold slightly for FakeEmbedder keyword-based matching
        extracted = extract_skills_from_profile(profile_text, competencies, threshold=0.25)

        assert len(extracted) > 0
        extracted_names = [item["name"] for item in extracted]
        # Should detect key skills mentioned in sample profile
        assert any(
            name in extracted_names
            for name in ["Survey Design", "Sampling Methods", "SQL", "Python for Data Analysis"]
        )

        for item in extracted:
            assert 1 <= item["level"] <= 4
            assert len(item["evidence"]) <= 3
            assert len(item["reasons"]) >= 1


# ==========================================
# 3. Profile Endpoints (Analyze, Self-Assessment, Skills Merge)
# ==========================================

def test_profile_endpoints_and_skills_merge(app, client, learner_token, learner_user):
    """
    Test POST /api/profile/analyze, PUT /api/profile/self-assessment,
    and GET /api/profile/skills with source averaging.
    """
    with app.app_context():
        seed_database(app)
        comp_sql = Competency.query.filter_by(name="SQL").first()
        comp_national = Competency.query.filter_by(name="National Accounts Basics").first()
        sql_id = comp_sql.id
        national_id = comp_national.id

    headers = {"Authorization": f"Bearer {learner_token}"}

    # 1. POST /api/profile/analyze (only mentions SQL and databases)
    profile_text = (
        "I have 3 years of experience writing SQL queries to manage relational databases.\n"
        "Built automated database scripts using SQL."
    )
    res_analyze = client.post(
        "/api/profile/analyze",
        json={"text": profile_text, "threshold": 0.25},
        headers=headers
    )
    assert res_analyze.status_code == 200
    analyze_data = res_analyze.get_json()
    assert analyze_data["extracted_count"] > 0

    # 2. PUT /api/profile/self-assessment
    # Give SQL a self-assessment of 4, and National Accounts a self-assessment of 3
    self_assess_payload = {
        sql_id: 4,
        national_id: 3
    }
    res_self = client.put(
        "/api/profile/self-assessment",
        json=self_assess_payload,
        headers=headers
    )
    assert res_self.status_code == 200
    assert res_self.get_json()["updated_count"] == 2

    # 3. GET /api/profile/skills (Merge Verification)
    res_skills = client.get("/api/profile/skills", headers=headers)
    assert res_skills.status_code == 200
    skills_data = res_skills.get_json()

    skills_by_id = {s["competency_id"]: s for s in skills_data["skills"]}

    # SQL had both profile extraction and self-assessment (4)
    assert sql_id in skills_by_id
    sql_skill = skills_by_id[sql_id]
    assert "profile" in sql_skill["sources"]
    assert "self" in sql_skill["sources"]
    # Verify average calculation: (profile_val + 4.0) / 2.0
    profile_val = sql_skill["source_breakdown"]["profile"]
    assert sql_skill["level"] == round((profile_val + 4.0) / 2.0, 2)

    # National Accounts only had self-assessment (3)
    assert national_id in skills_by_id
    national_skill = skills_by_id[national_id]
    assert national_skill["sources"] == ["self"]
    assert national_skill["level"] == 3.0


# ==========================================
# 4. Gap Analysis, Priority Weighting, and Prerequisite Blocking
# ==========================================

def test_gap_analysis_math_priority_and_blocking(app, client, learner_token, learner_user):
    """
    Test GET /api/gap?role_id=<id>:
      - gap = max(0, required - current)
      - priority = gap * (1 + dependents_in_role)
      - unmet prerequisite blocking flag
      - readiness percentage
    """
    with app.app_context():
        seed_database(app)
        role = Role.query.filter_by(name="Statistical Officer").first()
        role_id = role.id

        stats_comp = Competency.query.filter_by(name="Statistics Fundamentals").first()
        survey_comp = Competency.query.filter_by(name="Survey Design").first()
        sampling_comp = Competency.query.filter_by(name="Sampling Methods").first()
        stats_id = stats_comp.id
        survey_id = survey_comp.id
        sampling_id = sampling_comp.id

    headers = {"Authorization": f"Bearer {learner_token}"}

    # Initial state: learner has NO skills recorded.
    # For Statistical Officer, both Statistics Fundamentals and Sampling Methods require level 4.
    # Sampling Methods requires Statistics Fundamentals and Survey Design as prerequisites.
    res_gap = client.get(f"/api/gap?role_id={role_id}", headers=headers)
    assert res_gap.status_code == 200
    gap_data = res_gap.get_json()

    assert gap_data["role"]["id"] == role_id
    assert gap_data["readiness_percentage"] == 0.0  # No skills yet

    gap_items = {item["competency_id"]: item for item in gap_data["competencies"]}

    # Gap math: Level 0 current vs Level 4 required -> gap = 4
    stats_item = gap_items[stats_id]
    sampling_item = gap_items[sampling_id]

    assert stats_item["current_level"] == 0.0
    assert stats_item["required_level"] == 4
    assert stats_item["gap"] == 4.0

    # Priority weighting:
    # In seed data, Statistics Fundamentals is a prerequisite for Sampling Methods,
    # Regression and Forecasting, etc. (multiple dependents in Statistical Officer).
    # Therefore Statistics Fundamentals must have a higher priority score than Sampling Methods.
    assert stats_item["priority"] > sampling_item["priority"]

    # Prerequisite blocking flag:
    # Sampling Methods requires Statistics Fundamentals. Since user has gap in Statistics,
    # Sampling Methods must be marked as blocked!
    assert sampling_item["is_blocked"] is True
    blocked_by_names = [b["name"] for b in sampling_item["blocked_by"]]
    assert "Statistics Fundamentals" in blocked_by_names

    # Statistics Fundamentals itself has no unmet prerequisites, so it is NOT blocked
    assert stats_item["is_blocked"] is False

    # Now, satisfy both prerequisites (Statistics Fundamentals and Survey Design)
    client.put("/api/profile/self-assessment", json={stats_id: 4, survey_id: 4}, headers=headers)

    # Re-run gap analysis
    res_gap2 = client.get(f"/api/gap?role_id={role_id}", headers=headers)
    gap_data2 = res_gap2.get_json()
    gap_items2 = {item["competency_id"]: item for item in gap_data2["competencies"]}

    # Statistics Fundamentals gap is now 0 and priority is 0
    assert gap_data2["readiness_percentage"] > 0.0
    assert gap_items2[stats_id]["gap"] == 0.0
    assert gap_items2[stats_id]["priority"] == 0.0

    # Prerequisite blocking should now be resolved for Sampling Methods!
    assert gap_items2[sampling_id]["is_blocked"] is False


# ==========================================
# 5. Permission & Error Handling Tests
# ==========================================

def test_permissions_and_validation(client):
    """Endpoints require authentication and validate request inputs."""
    # Unauthenticated requests return 401
    assert client.post("/api/profile/analyze", json={"text": "Hello"}).status_code == 401
    assert client.put("/api/profile/self-assessment", json={"1": 3}).status_code == 401
    assert client.get("/api/profile/skills").status_code == 401
    assert client.get("/api/gap?role_id=1").status_code == 401


def test_gap_endpoint_validation(client, learner_token):
    """GET /api/gap validates presence and validity of role_id."""
    headers = {"Authorization": f"Bearer {learner_token}"}

    # Missing role_id -> 400
    res_missing = client.get("/api/gap", headers=headers)
    assert res_missing.status_code == 400

    # Invalid role_id type -> 400
    res_invalid = client.get("/api/gap?role_id=abc", headers=headers)
    assert res_invalid.status_code == 400

    # Non-existent role -> 404
    res_404 = client.get("/api/gap?role_id=99999", headers=headers)
    assert res_404.status_code == 404
