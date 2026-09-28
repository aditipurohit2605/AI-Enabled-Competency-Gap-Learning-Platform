import pytest
from backend.app.extensions import db
from backend.app.models.competency import Competency, Role, Prerequisite, RoleCompetency
from backend.seed import seed_database


# ==========================================
# 1. Admin-Only Access Tests
# ==========================================

def test_competency_crud_permissions(client, learner_token, trainer_token, admin_token):
    """Mutations on /api/competencies require admin; reads are open to any authenticated user."""
    # Read without token -> 401
    assert client.get("/api/competencies").status_code == 401

    # Read with learner token -> 200
    res_get = client.get("/api/competencies", headers={"Authorization": f"Bearer {learner_token}"})
    assert res_get.status_code == 200

    # Create as learner -> 403
    payload = {"name": "New Skill", "description": "Testing permissions"}
    res_post_learner = client.post(
        "/api/competencies",
        json=payload,
        headers={"Authorization": f"Bearer {learner_token}"}
    )
    assert res_post_learner.status_code == 403

    # Create as trainer -> 403
    res_post_trainer = client.post(
        "/api/competencies",
        json=payload,
        headers={"Authorization": f"Bearer {trainer_token}"}
    )
    assert res_post_trainer.status_code == 403

    # Create as admin -> 201
    res_post_admin = client.post(
        "/api/competencies",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_post_admin.status_code == 201
    created_id = res_post_admin.get_json()["competency"]["id"]

    # Update as learner -> 403
    res_put_learner = client.put(
        f"/api/competencies/{created_id}",
        json={"description": "Updated"},
        headers={"Authorization": f"Bearer {learner_token}"}
    )
    assert res_put_learner.status_code == 403

    # Update as admin -> 200
    res_put_admin = client.put(
        f"/api/competencies/{created_id}",
        json={"description": "Updated by admin"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_put_admin.status_code == 200

    # Delete as learner -> 403
    res_del_learner = client.delete(
        f"/api/competencies/{created_id}",
        headers={"Authorization": f"Bearer {learner_token}"}
    )
    assert res_del_learner.status_code == 403

    # Delete as admin -> 200
    res_del_admin = client.delete(
        f"/api/competencies/{created_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_del_admin.status_code == 200


def test_role_crud_permissions(client, learner_token, admin_token):
    """Mutations on /api/roles require admin; reads are open to any authenticated user."""
    # List roles as learner -> 200
    res = client.get("/api/roles", headers={"Authorization": f"Bearer {learner_token}"})
    assert res.status_code == 200

    # Create role as learner -> 403
    payload = {"name": "Test Role", "description": "Desc"}
    res_create_learner = client.post(
        "/api/roles",
        json=payload,
        headers={"Authorization": f"Bearer {learner_token}"}
    )
    assert res_create_learner.status_code == 403

    # Create role as admin -> 201
    res_create_admin = client.post(
        "/api/roles",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_create_admin.status_code == 201
    role_id = res_create_admin.get_json()["role"]["id"]

    # Delete role as admin -> 200
    res_delete = client.delete(f"/api/roles/{role_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_delete.status_code == 200


# ==========================================
# 2. Validation Errors Tests
# ==========================================

def test_competency_validation_errors(client, admin_token):
    """Test required fields, non-empty validation, and duplicate conflict."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Missing name
    res = client.post("/api/competencies", json={"description": "Missing name"}, headers=headers)
    assert res.status_code == 400

    # Empty name
    res = client.post("/api/competencies", json={"name": "   "}, headers=headers)
    assert res.status_code == 400

    # Create valid competency
    res1 = client.post("/api/competencies", json={"name": "Unique Skill"}, headers=headers)
    assert res1.status_code == 201

    # Duplicate name conflict
    res2 = client.post("/api/competencies", json={"name": "Unique Skill"}, headers=headers)
    assert res2.status_code == 409

    # Non-existent competency
    res_404 = client.get("/api/competencies/99999", headers=headers)
    assert res_404.status_code == 404


def test_role_competencies_validation(client, admin_token):
    """Test validation when setting required levels for a role."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create role and competency
    res_role = client.post("/api/roles", json={"name": "Analyst"}, headers=headers)
    role_id = res_role.get_json()["role"]["id"]

    res_comp = client.post("/api/competencies", json={"name": "Python"}, headers=headers)
    comp_id = res_comp.get_json()["competency"]["id"]

    # Invalid required_level: 0 (must be 1-5)
    res_inv0 = client.post(
        f"/api/roles/{role_id}/competencies",
        json={"competency_id": comp_id, "required_level": 0},
        headers=headers
    )
    assert res_inv0.status_code == 400

    # Invalid required_level: 6 (must be 1-5)
    res_inv6 = client.post(
        f"/api/roles/{role_id}/competencies",
        json={"competency_id": comp_id, "required_level": 6},
        headers=headers
    )
    assert res_inv6.status_code == 400

    # Valid required_level: 4
    res_valid = client.post(
        f"/api/roles/{role_id}/competencies",
        json={"competency_id": comp_id, "required_level": 4},
        headers=headers
    )
    assert res_valid.status_code == 200

    # Non-existent role
    res_no_role = client.post(
        "/api/roles/99999/competencies",
        json={"competency_id": comp_id, "required_level": 3},
        headers=headers
    )
    assert res_no_role.status_code == 404

    # Non-existent competency
    res_no_comp = client.post(
        f"/api/roles/{role_id}/competencies",
        json={"competency_id": 99999, "required_level": 3},
        headers=headers
    )
    assert res_no_comp.status_code == 404


# ==========================================
# 3. Cycle Rejection & Self-Reference Tests
# ==========================================

def test_prerequisite_self_reference_rejection(client, admin_token):
    """Self-referencing prerequisites (A requires A) must be rejected with 400."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    res_comp = client.post("/api/competencies", json={"name": "SelfRef Comp"}, headers=headers)
    comp_id = res_comp.get_json()["competency"]["id"]

    res = client.post(
        "/api/prerequisites",
        json={"competency_id": comp_id, "requires_competency_id": comp_id},
        headers=headers
    )
    assert res.status_code == 400
    assert "cannot require itself" in res.get_json()["message"]


def test_prerequisite_direct_2_node_cycle_rejection(client, admin_token):
    """Direct cycle A requires B, and B requires A must be rejected."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    c1 = client.post("/api/competencies", json={"name": "A"}, headers=headers).get_json()["competency"]["id"]
    c2 = client.post("/api/competencies", json={"name": "B"}, headers=headers).get_json()["competency"]["id"]

    # B requires A (A -> B)
    res1 = client.post(
        "/api/prerequisites",
        json={"competency_id": c2, "requires_competency_id": c1},
        headers=headers
    )
    assert res1.status_code == 201

    # Attempting to make A require B (B -> A) creates cycle A -> B -> A
    res2 = client.post(
        "/api/prerequisites",
        json={"competency_id": c1, "requires_competency_id": c2},
        headers=headers
    )
    assert res2.status_code == 400
    data = res2.get_json()
    assert "circular dependency" in data["message"].lower() or "cycle" in data["message"].lower()


def test_prerequisite_multi_node_cycle_rejection(client, admin_token):
    """Multi-node cycle A -> B -> C, then attempting C -> A must be rejected."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    c1 = client.post("/api/competencies", json={"name": "Node A"}, headers=headers).get_json()["competency"]["id"]
    c2 = client.post("/api/competencies", json={"name": "Node B"}, headers=headers).get_json()["competency"]["id"]
    c3 = client.post("/api/competencies", json={"name": "Node C"}, headers=headers).get_json()["competency"]["id"]

    # B requires A
    res1 = client.post("/api/prerequisites", json={"competency_id": c2, "requires_competency_id": c1}, headers=headers)
    assert res1.status_code == 201

    # C requires B
    res2 = client.post("/api/prerequisites", json={"competency_id": c3, "requires_competency_id": c2}, headers=headers)
    assert res2.status_code == 201

    # A requires C -> cycle A -> B -> C -> A
    res3 = client.post("/api/prerequisites", json={"competency_id": c1, "requires_competency_id": c3}, headers=headers)
    assert res3.status_code == 400
    assert "circular dependency" in res3.get_json()["message"].lower() or "cycle" in res3.get_json()["message"].lower()


# ==========================================
# 4. Seed Idempotency Test
# ==========================================

def test_seed_database_idempotency(app):
    """Running seed_database repeatedly must succeed without duplicating records or raising errors."""
    with app.app_context():
        # First execution
        counts1 = seed_database(app)
        assert counts1["competencies_count"] == 12
        assert counts1["roles_count"] == 4
        assert counts1["users_count"] == 5

        comp_count_db1 = Competency.query.count()
        role_count_db1 = Role.query.count()
        prereq_count_db1 = Prerequisite.query.count()

        assert comp_count_db1 == 12
        assert role_count_db1 == 4

        # Second execution (idempotency check)
        counts2 = seed_database(app)
        assert counts2["competencies_count"] == 12
        assert counts2["roles_count"] == 4

        comp_count_db2 = Competency.query.count()
        role_count_db2 = Role.query.count()
        prereq_count_db2 = Prerequisite.query.count()

        assert comp_count_db2 == comp_count_db1
        assert role_count_db2 == role_count_db1
        assert prereq_count_db2 == prereq_count_db1


# ==========================================
# 5. Role Framework Endpoint Test
# ==========================================

def test_get_role_framework_endpoint(app, client, learner_token):
    """GET /api/roles/<id>/framework returns the role's competencies, required levels, and prerequisites."""
    # Seed the database
    with app.app_context():
        seed_database(app)
        officer_role = Role.query.filter_by(name="Statistical Officer").first()
        role_id = officer_role.id

    headers = {"Authorization": f"Bearer {learner_token}"}
    response = client.get(f"/api/roles/{role_id}/framework", headers=headers)
    assert response.status_code == 200

    data = response.get_json()
    assert "role" in data
    assert data["role"]["name"] == "Statistical Officer"
    assert "competencies" in data
    assert len(data["competencies"]) == 12

    # Check that required levels and prerequisites are present
    sampling_comp = next(
        (c for c in data["competencies"] if c["name"] == "Sampling Methods"),
        None
    )
    assert sampling_comp is not None
    assert sampling_comp["required_level"] == 4
    prereq_names = [p["name"] for p in sampling_comp["prerequisites"]]
    assert "Statistics Fundamentals" in prereq_names


def test_get_role_framework_not_found(client, learner_token):
    """GET /api/roles/<id>/framework returns 404 if role does not exist."""
    headers = {"Authorization": f"Bearer {learner_token}"}
    response = client.get("/api/roles/99999/framework", headers=headers)
    assert response.status_code == 404
