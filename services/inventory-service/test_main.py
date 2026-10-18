import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["service"] == "inventory-service"


def test_create_and_get_inventory(client):
    response = client.put(
        "/inventory/101",
        json={"quantity": 20},
    )

    assert response.status_code == 200
    assert response.json()["quantity"] == 20

    response = client.get("/inventory/101")

    assert response.status_code == 200
    assert response.json() == {
        "product_id": 101,
        "quantity": 20,
    }


def test_reserve_stock(client):
    client.put("/inventory/102", json={"quantity": 10})

    response = client.post(
        "/inventory/reserve",
        json={"product_id": 102, "quantity": 3},
    )

    assert response.status_code == 200
    assert response.json()["remaining_quantity"] == 7


def test_reserve_insufficient_stock(client):
    client.put("/inventory/103", json={"quantity": 2})

    response = client.post(
        "/inventory/reserve",
        json={"product_id": 103, "quantity": 5},
    )

    assert response.status_code == 409

    stock = client.get("/inventory/103")
    assert stock.json()["quantity"] == 2


def test_reserve_missing_product(client):
    response = client.post(
        "/inventory/reserve",
        json={"product_id": 999, "quantity": 1},
    )

    assert response.status_code == 404


def test_restock(client):
    client.put("/inventory/104", json={"quantity": 5})

    response = client.post(
        "/inventory/restock",
        json={"product_id": 104, "quantity": 4},
    )

    assert response.status_code == 200
    assert response.json()["quantity"] == 9


def test_restock_missing_product(client):
    response = client.post(
        "/inventory/restock",
        json={"product_id": 998, "quantity": 2},
    )

    assert response.status_code == 404


def test_negative_stock_rejected(client):
    response = client.put(
        "/inventory/105",
        json={"quantity": -1},
    )

    assert response.status_code == 422
