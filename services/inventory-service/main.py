
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import update
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Inventory


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="E-Commerce Inventory Service",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow requests from the local ShopSphere frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


DbSession = Annotated[Session, Depends(get_db)]


class StockRequest(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class StockUpdateRequest(BaseModel):
    quantity: int = Field(ge=0)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "inventory-service",
    }


@app.get("/inventory/{product_id}")
def get_inventory(product_id: int, db: DbSession):
    item = db.get(Inventory, product_id)

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory record not found",
        )

    return {
        "product_id": item.product_id,
        "quantity": item.quantity,
    }


@app.put("/inventory/{product_id}")
def set_inventory(
    product_id: int,
    request: StockUpdateRequest,
    db: DbSession,
):
    item = db.get(Inventory, product_id)

    if item is None:
        item = Inventory(
            product_id=product_id,
            quantity=request.quantity,
        )
        db.add(item)
    else:
        item.quantity = request.quantity

    db.commit()
    db.refresh(item)

    return {
        "message": "Inventory updated",
        "product_id": item.product_id,
        "quantity": item.quantity,
    }


@app.post("/inventory/reserve")
def reserve_stock(request: StockRequest, db: DbSession):
    statement = (
        update(Inventory)
        .where(
            Inventory.product_id == request.product_id,
            Inventory.quantity >= request.quantity,
        )
        .values(quantity=Inventory.quantity - request.quantity)
        .returning(Inventory.product_id, Inventory.quantity)
    )

    result = db.execute(statement).first()

    if result is None:
        db.rollback()

        exists = db.get(Inventory, request.product_id)

        if exists is None:
            raise HTTPException(
                status_code=404,
                detail="Inventory record not found",
            )

        raise HTTPException(
            status_code=409,
            detail="Insufficient stock",
        )

    db.commit()

    return {
        "message": "Stock reserved",
        "product_id": result.product_id,
        "remaining_quantity": result.quantity,
    }


@app.post("/inventory/restock")
def restock_stock(request: StockRequest, db: DbSession):
    statement = (
        update(Inventory)
        .where(Inventory.product_id == request.product_id)
        .values(quantity=Inventory.quantity + request.quantity)
        .returning(Inventory.product_id, Inventory.quantity)
    )

    result = db.execute(statement).first()

    if result is None:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail="Inventory record not found",
        )

    db.commit()

    return {
        "message": "Stock restored",
        "product_id": result.product_id,
        "quantity": result.quantity,
    }
