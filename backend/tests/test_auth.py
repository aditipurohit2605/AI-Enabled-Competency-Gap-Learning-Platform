def test_register_success_default_role(client):
    """Registering a new user without specifying role should default to 'learner'."""
    payload = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "password": "securepassword123"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert "token" in data
    assert data["user"]["name"] == "Jane Doe"
    assert data["user"]["email"] == "jane@example.com"
    assert data["user"]["role"] == "learner"


def test_register_with_trainer_role(client):
    """Registering a trainer user should persist role as 'trainer'."""
    payload = {
        "name": "Trainer Sam",
        "email": "sam@example.com",
        "password": "securepassword123",
        "role": "trainer"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["user"]["role"] == "trainer"


def test_register_duplicate_email(client, learner_user):
    """Registering an email that already exists should return 409 Conflict."""
    payload = {
        "name": "Duplicate Alice",
        "email": learner_user["email"],
        "password": "password123"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 409
    data = response.get_json()
    assert data["error"] == "Conflict"


def test_register_invalid_inputs(client):
    """Missing or invalid fields should return 400 Bad Request."""
    # Missing name
    res = client.post("/api/auth/register", json={"email": "a@b.com", "password": "pass12345"})
    assert res.status_code == 400

    # Missing email
    res = client.post("/api/auth/register", json={"name": "Alice", "password": "pass12345"})
    assert res.status_code == 400

    # Malformed email
    res = client.post("/api/auth/register", json={"name": "Alice", "email": "not-an-email", "password": "pass12345"})
    assert res.status_code == 400

    # Short password
    res = client.post("/api/auth/register", json={"name": "Alice", "email": "a@b.com", "password": "123"})
    assert res.status_code == 400

    # Invalid role
    res = client.post("/api/auth/register", json={
        "name": "Alice",
        "email": "a@b.com",
        "password": "password123",
        "role": "superhero"
    })
    assert res.status_code == 400


def test_login_success(client, learner_user):
    """Valid credentials should return JWT token and user info."""
    response = client.post("/api/auth/login", json={
        "email": learner_user["email"],
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.get_json()
    assert "token" in data
    assert data["user"]["email"] == learner_user["email"]


def test_login_invalid_password(client, learner_user):
    """Wrong password should return 401 Unauthorized."""
    response = client.post("/api/auth/login", json={
        "email": learner_user["email"],
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    assert response.get_json()["error"] == "Unauthorized"


def test_login_nonexistent_user(client):
    """Non-existent user should return 401 Unauthorized."""
    response = client.post("/api/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "password123"
    })
    assert response.status_code == 401


def test_me_endpoint_with_valid_token(client, learner_token, learner_user):
    """GET /api/auth/me with valid Bearer token should return user profile."""
    headers = {"Authorization": f"Bearer {learner_token}"}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["user"]["email"] == learner_user["email"]
    assert data["user"]["role"] == "learner"


def test_me_endpoint_without_token(client):
    """GET /api/auth/me without token should return 401 Unauthorized."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
