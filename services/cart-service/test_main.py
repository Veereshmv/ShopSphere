
import json

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client():
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def isolated_cart():
    """Use a dedicated Redis key so existing cart data stays untouched."""
    user_id = "pytest-cart-user"

    yield user_id

    main.redis_client.delete(f"cart:{user_id}")


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "cart-service",
    }


def test_add_new_item(client, isolated_cart):
    response = client.post(
        f"/cart/{isolated_cart}/items",
        json={
            "product_id": 101,
            "name": "Test Mouse",
            "price": 25.0,
            "quantity": 1,
        },
    )

    assert response.status_code == 200
    assert response.json()["item"]["quantity"] == 1


def test_increase_existing_item_quantity(client, isolated_cart):
    payload = {
        "product_id": 102,
        "name": "Test Keyboard",
        "price": 50.0,
        "quantity": 2,
    }

    first = client.post(
        f"/cart/{isolated_cart}/items",
        json=payload,
    )
    assert first.status_code == 200

    payload["quantity"] = 3

    second = client.post(
        f"/cart/{isolated_cart}/items",
        json=payload,
    )

    assert second.status_code == 200
    assert second.json()["item"]["quantity"] == 5


def test_get_cart(client, isolated_cart):
    client.post(
        f"/cart/{isolated_cart}/items",
        json={
            "product_id": 103,
            "name": "Test Hub",
            "price": 15.0,
            "quantity": 2,
        },
    )

    response = client.get(f"/cart/{isolated_cart}")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["items"][0]["product_id"] == 103
    assert data["items"][0]["quantity"] == 2


def test_remove_item(client, isolated_cart):
    client.post(
        f"/cart/{isolated_cart}/items",
        json={
            "product_id": 104,
            "name": "Temporary Item",
            "price": 10.0,
            "quantity": 1,
        },
    )

    response = client.delete(
        f"/cart/{isolated_cart}/items/104"
    )

    assert response.status_code == 200

    cart = client.get(f"/cart/{isolated_cart}").json()
    assert cart["count"] == 0


def test_remove_missing_item_returns_404(client, isolated_cart):
    response = client.delete(
        f"/cart/{isolated_cart}/items/999"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Cart item not found"


def test_clear_cart(client, isolated_cart):
    client.post(
        f"/cart/{isolated_cart}/items",
        json={
            "product_id": 105,
            "name": "Temporary Item",
            "price": 10.0,
            "quantity": 1,
        },
    )

    response = client.delete(f"/cart/{isolated_cart}")

    assert response.status_code == 200

    cart = client.get(f"/cart/{isolated_cart}").json()
    assert cart["count"] == 0


def test_invalid_item_is_rejected(client, isolated_cart):
    response = client.post(
        f"/cart/{isolated_cart}/items",
        json={
            "product_id": 0,
            "name": "Invalid Item",
            "price": 10.0,
            "quantity": 1,
        },
    )

    assert response.status_code == 422
