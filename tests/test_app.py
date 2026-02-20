def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Welcome to Policy AI Agent API"
    assert payload["version"] == "1.0.0"


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert "timestamp" in payload


def test_root_includes_docs(client):
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert "docs" in payload
    assert payload["docs"] == "/docs"
