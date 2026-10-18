
import json
import os
from contextlib import asynccontextmanager

import redis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client.ping()
    yield
    redis_client.close()


app = FastAPI(
    title="ShopSphere Cart Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CartItemRequest(BaseModel):
    product_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=150)
    price: float = Field(gt=0)
    quantity: int = Field(default=1, gt=0)


def get_cart_items(user_id: str):
    items = redis_client.hgetall(f"cart:{user_id}")
    return [json.loads(value) for value in items.values()]


def get_cart(user_id: str):
    cart_items = get_cart_items(user_id)

    total = sum(
        item["price"] * item["quantity"]
        for item in cart_items
    )

    return {
        "user_id": user_id,
        "count": len(cart_items),
        "items": cart_items,
        "total": round(total, 2),
    }


@app.get("/health")
def health():
    return {"status": "healthy", "service": "cart-service"}


@app.post("/cart/{user_id}/items")
def add_item(user_id: str, item: CartItemRequest):
    if not user_id.strip():
        raise HTTPException(
            status_code=400,
            detail="User ID cannot be empty",
        )

    cart_key = f"cart:{user_id}"
    product_key = str(item.product_id)
    existing = redis_client.hget(cart_key, product_key)

    if existing:
        existing_item = json.loads(existing)
        existing_item["quantity"] += item.quantity
        redis_client.hset(
            cart_key,
            product_key,
            json.dumps(existing_item),
        )
    else:
        redis_client.hset(
            cart_key,
            product_key,
            item.model_dump_json(),
        )

    return {
        "item": json.loads(
            redis_client.hget(cart_key, product_key)
        ),
        **get_cart(user_id),
    }


@app.get("/cart/{user_id}")
def read_cart(user_id: str):
    return get_cart(user_id)


@app.delete("/cart/{user_id}/items/{product_id}")
def remove_item(user_id: str, product_id: int):
    cart_key = f"cart:{user_id}"
    removed = redis_client.hdel(cart_key, str(product_id))

    if not removed:
        raise HTTPException(
            status_code=404,
            detail="Cart item not found",
        )

    return get_cart(user_id)


@app.delete("/cart/{user_id}")
def clear_cart(user_id: str):
    redis_client.delete(f"cart:{user_id}")
    return get_cart(user_id)
