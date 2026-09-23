from app.services import health_service


def test_readiness_checks_database(client):
    assert client.get("/health/ready").json() == {"status": "ok", "database": "ready"}


def test_readiness_does_not_expose_database_errors(client, monkeypatch):
    def fail():
        raise RuntimeError("database-password")

    monkeypatch.setattr(health_service, "session_scope", fail)
    response = client.get("/health/ready")
    assert response.status_code == 503 and "database-password" not in response.text
