from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_cors_allows_localhost_port_3001():
    response = client.options(
        "/api/auth/login/json",
        headers={
            "Origin": "http://localhost:3001",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3001"
