
from contextlib import asynccontextmanager
from decimal import Decimal, ROUND_HALF_UP

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database import Base, engine, get_db
from models import Order, OrderItem


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="E-Commerce Order Service",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow the local ShopSphere frontend to call this service.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OrderItemRequest(BaseModel):
    product_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=150)
    unit_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    quantity: int = Field(gt=0)


class CreateOrderRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    items: list[OrderItemRequest] = Field(min_length=1)


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    name: str
    unit_price: Decimal
    quantity: int


class OrderResponse(BaseModel):
    id: int
    user_id: str
    status: str
    total_amount: Decimal
    created_at: str
    items: list[OrderItemResponse]


def serialize_order(order: Order) -> dict:
    return {
        "id": order.id,
        "user_id": order.user_id,
        "status": order.status,
        "total_amount": order.total_amount,
        "created_at": order.created_at.isoformat(),
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "name": item.name,
                "unit_price": item.unit_price,
                "quantity": item.quantity,
            }
            for item in order.items
        ],
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "order-service",
    }


@app.post("/orders", status_code=status.HTTP_201_CREATED)
def create_order(
    request: CreateOrderRequest,
    db: Session = Depends(get_db),
):
    total = sum(
        (item.unit_price * item.quantity for item in request.items),
        Decimal("0.00"),
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    order = Order(
        user_id=request.user_id,
        status="pending",
        total_amount=total,
        items=[
            OrderItem(
                product_id=item.product_id,
                name=item.name,
                unit_price=item.unit_price,
                quantity=item.quantity,
            )
            for item in request.items
        ],
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    saved_order = db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order.id)
    )

    return serialize_order(saved_order)


@app.get("/orders/{order_id}")
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
):
    order = db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id)
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return serialize_order(order)


@app.get("/orders/user/{user_id}")
def get_user_orders(
    user_id: str,
    db: Session = Depends(get_db),
):
    orders = db.scalars(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc(), Order.id.desc())
    ).all()

    return {
        "user_id": user_id,
        "orders": [serialize_order(order) for order in orders],
        "count": len(orders),
    }
