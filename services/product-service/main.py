from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Product


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    # Seed the catalog only when it is empty.
    with Session(engine) as db:
        existing_product = db.scalar(select(Product.id).limit(1))

        if existing_product is None:
            db.add_all([
                Product(
                    name="Wireless Mouse",
                    description="Ergonomic wireless mouse",
                    price=799.00,
                    stock=50,
                ),
                Product(
                    name="Mechanical Keyboard",
                    description="Mechanical keyboard with tactile switches",
                    price=2499.00,
                    stock=30,
                ),
                Product(
                    name="USB-C Hub",
                    description="Multiport USB-C adapter",
                    price=1499.00,
                    stock=25,
                ),
            ])
            db.commit()

    yield


app = FastAPI(
    title="ShopSphere Product Service",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow requests from our local HTML frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "product-service",
    }


@app.get("/products")
def list_products(db: Session = Depends(get_db)):
    return db.scalars(select(Product).order_by(Product.id)).all()


@app.get("/products/{product_id}")
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return product
