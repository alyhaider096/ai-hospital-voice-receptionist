from fastapi.testclient import TestClient


def test_admin_summary_requires_auth(client: TestClient) -> None:
    response = client.get("/admin/dashboard/summary")

    assert response.status_code == 401


def test_admin_summary_returns_counts(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.get("/admin/dashboard/summary", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["doctors"] == 5
    assert data["patients"] == 0
    assert data["appointments"] == 0
    assert data["call_logs"] == 0

