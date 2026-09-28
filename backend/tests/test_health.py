def test_health_check_endpoint(client):
    """GET /api/health should return 200 OK and health status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert "service" in data
    assert "version" in data


def test_health_check_root_alias(client):
    """GET /health alias should also return 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
