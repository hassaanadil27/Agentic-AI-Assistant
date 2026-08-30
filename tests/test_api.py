from fastapi.testclient import TestClient

from api import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_portfolio_and_quality_endpoints():
    with TestClient(app) as client:
        portfolio = client.get("/api/portfolio")
        quality = client.get("/api/data-quality")
    assert portfolio.status_code == 200
    assert portfolio.json()["metadata"]["total_projects"] > 0
    assert quality.status_code == 200
    assert quality.json()["total_rows"] > 0


def test_query_validation():
    with TestClient(app) as client:
        response = client.post("/api/query", json={"question": ""})
    assert response.status_code == 422


def test_query_returns_validated_evidence_contract(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    with TestClient(app) as client:
        response = client.post("/api/query", json={"question": "What is the average project cost?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["validation"] == "passed"
    assert payload["evidence"]["dataset"] == "Projects.xlsx"
    assert payload["evidence"]["operation"] == "mean"
    assert payload["table"] and payload["chart"] is None
