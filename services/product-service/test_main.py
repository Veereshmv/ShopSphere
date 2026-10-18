
import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "product-service",
    }


def test_list_products(client):
    response = client.get("/products")

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3


def test_get_product(client):
    response = client.get("/products/1")

    assert response.status_code == 200
    assert response.json()["name"] == "Wireless Mouse"


def test_get_nonexistent_product(client):
    response = client.get("/products/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"
