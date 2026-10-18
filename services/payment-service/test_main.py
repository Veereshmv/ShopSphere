import pytest
from fastapi.testclient import TestClient

from main import app, payments, payments_lock


@pytest.fixture
def client():
    with payments_lock:
        payments.clear()

    with TestClient(app) as test_client:
        yield test_client

    with payments_lock:
        payments.clear()


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["service"] == "payment-service"


def test_successful_payment(client):
    response = client.post(
        "/payments",
        json={
            "order_id": 1,
            "user_id": "test-user",
            "amount": "4097.00",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["order_id"] == 1
    assert data["user_id"] == "test-user"
    assert float(data["amount"]) == 4097.00
    assert data["status"] == "succeeded"
    assert data["payment_id"]


def test_simulated_payment_failure(client):
    response = client.post(
        "/payments",
        json={
            "order_id": 2,
            "user_id": "test-user",
            "amount": "100.00",
            "simulate_failure": True,
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "failed"


def test_get_payment(client):
    created = client.post(
        "/payments",
        json={
            "order_id": 3,
            "user_id": "test-user",
            "amount": "250.00",
        },
    ).json()

    response = client.get(f"/payments/{created['payment_id']}")

    assert response.status_code == 200
    assert response.json()["payment_id"] == created["payment_id"]


def test_missing_payment_returns_404(client):
    response = client.get("/payments/unknown-payment-id")

    assert response.status_code == 404
    assert response.json()["detail"] == "Payment not found"


def test_nonpositive_amount_is_rejected(client):
    response = client.post(
        "/payments",
        json={
            "order_id": 4,
            "user_id": "test-user",
            "amount": "0.00",
        },
    )

    assert response.status_code == 422


def test_missing_required_field_is_rejected(client):
    response = client.post(
        "/payments",
        json={
            "order_id": 5,
            "amount": "100.00",
        },
    )

    assert response.status_code == 422
