import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.parametrize("path", ["/api/products", "/api/orders", "/api/inventory", "/api/delivery-routes"])
def test_collection_routes_accept_missing_trailing_slash(path):
    response = client.get(path, follow_redirects=False)
    assert response.status_code != 404
