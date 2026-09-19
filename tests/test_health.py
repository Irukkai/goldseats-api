"""Health endpoint contract — the CI smoke test for the whole app wiring."""

from fastapi.testclient import TestClient


def test_health_reports_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "test", "version": "0.1.0"}


def test_health_is_also_served_unprefixed(client: TestClient) -> None:
    assert client.get("/health").status_code == 200


def test_ready_reports_database_reachable(client: TestClient) -> None:
    response = client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": True}


def test_every_response_carries_a_request_id(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.headers["x-request-id"]


def test_request_id_is_echoed_when_supplied(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"x-request-id": "abc-123"})

    assert response.headers["x-request-id"] == "abc-123"


def test_openapi_schema_is_available_outside_production(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    assert schema["info"]["title"] == "GoldSeats API"
    assert "/api/v1/health" in schema["paths"]
