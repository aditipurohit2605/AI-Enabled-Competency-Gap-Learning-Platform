def test_protected_endpoint_without_token(client):
    """Protected endpoints require Authorization header, returning 401 if missing."""
    res_admin = client.get("/api/auth/role-test/admin")
    assert res_admin.status_code == 401

    res_trainer = client.get("/api/auth/role-test/trainer")
    assert res_trainer.status_code == 401

    res_learner = client.get("/api/auth/role-test/learner")
    assert res_learner.status_code == 401


def test_protected_endpoint_malformed_header(client):
    """Malformed Authorization headers should return 401 Unauthorized."""
    # Not Bearer
    res = client.get("/api/auth/role-test/admin", headers={"Authorization": "Basic 12345"})
    assert res.status_code == 401

    # Just 'Bearer' with no token
    res = client.get("/api/auth/role-test/admin", headers={"Authorization": "Bearer"})
    assert res.status_code == 401

    # Invalid JWT token
    res = client.get("/api/auth/role-test/admin", headers={"Authorization": "Bearer invalid.jwt.token"})
    assert res.status_code == 401


def test_admin_endpoint_permissions(client, learner_token, trainer_token, admin_token):
    """Only admins should be permitted to access admin-only endpoints."""
    # Learner access -> 403 Forbidden
    res_learner = client.get(
        "/api/auth/role-test/admin",
        headers={"Authorization": f"Bearer {learner_token}"}
    )
    assert res_learner.status_code == 403
    assert res_learner.get_json()["error"] == "Forbidden"

    # Trainer access -> 403 Forbidden
    res_trainer = client.get(
        "/api/auth/role-test/admin",
        headers={"Authorization": f"Bearer {trainer_token}"}
    )
    assert res_trainer.status_code == 403

    # Admin access -> 200 OK
    res_admin = client.get(
        "/api/auth/role-test/admin",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_admin.status_code == 200
    assert res_admin.get_json()["message"] == "Admin access granted"


def test_trainer_or_admin_endpoint_permissions(client, learner_token, trainer_token, admin_token):
    """Trainer and Admin should have access, but not Learner."""
    # Learner access -> 403 Forbidden
    res_learner = client.get(
        "/api/auth/role-test/trainer",
        headers={"Authorization": f"Bearer {learner_token}"}
    )
    assert res_learner.status_code == 403

    # Trainer access -> 200 OK
    res_trainer = client.get(
        "/api/auth/role-test/trainer",
        headers={"Authorization": f"Bearer {trainer_token}"}
    )
    assert res_trainer.status_code == 200
    assert res_trainer.get_json()["message"] == "Trainer/Admin access granted"

    # Admin access -> 200 OK
    res_admin = client.get(
        "/api/auth/role-test/trainer",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_admin.status_code == 200


def test_learner_endpoint_permissions(client, learner_token, trainer_token):
    """Learner endpoint should be accessible by learner, but not trainer."""
    res_learner = client.get(
        "/api/auth/role-test/learner",
        headers={"Authorization": f"Bearer {learner_token}"}
    )
    assert res_learner.status_code == 200
    assert res_learner.get_json()["message"] == "Learner access granted"

    res_trainer = client.get(
        "/api/auth/role-test/learner",
        headers={"Authorization": f"Bearer {trainer_token}"}
    )
    assert res_trainer.status_code == 403
