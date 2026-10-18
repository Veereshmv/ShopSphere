from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from database import Base, get_db


@pytest.fixture
def client(monkeypatch):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(main, "engine", test_engine)
    main.app.dependency_overrides[get_db] = override_get_db

    with TestClient(main.app) as test_client:
        yield test_client

    main.app.dependency_overrides.clear()
    test_engine.dispose()


def sample_order():
    return {
        "user_id": "test-user",
        "items": [
            {
                "product_id": 1,
                "name": "Wireless Mouse",
                "unit_price": "799.00",
                "quantity": 2,
            },
            {
                "product_id": 2,
                "name": "Mechanical Keyboard",
                "unit_price": "2499.00",
                "quantity": 1,
            },
        ],
    }


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["service"] == "order-service"


def test_create_order_calculates_total(client):
    response = client.post("/orders", json=sample_order())

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == "test-user"
    assert data["status"] == "pending"
    assert Decimal(data["total_amount"]) == Decimal("4097.00")
    assert len(data["items"]) == 2


def test_get_order(client):
    created = client.post("/orders", json=sample_order()).json()

    response = client.get(f"/orders/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert len(response.json()["items"]) == 2


def test_missing_order_returns_404(client):
    response = client.get("/orders/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_get_user_order_history(client):
    client.post("/orders", json=sample_order())
    client.post("/orders", json=sample_order())

    response = client.get("/orders/user/test-user")

    assert response.status_code == 200
    assert response.json()["count"] == 2


def test_empty_order_is_rejected(client):
    payload = {"user_id": "test-user", "items": []}

    response = client.post("/orders", json=payload)

    assert response.status_code == 422


def test_nonpositive_quantity_is_rejected(client):
    payload = {
        "user_id": "test-user",
        "items": [
            {
                "product_id": 1,
                "name": "Wireless Mouse",
                "unit_price": "799.00",
                "quantity": 0,
            }
        ],
    }

    response = client.post("/orders", json=payload)

    assert response.status_code == 422
