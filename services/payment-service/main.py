
from decimal import Decimal
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


app = FastAPI(
    title="E-Commerce Payment Service",
    version="1.0.0",
)

# Allow requests from the local ShopSphere frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

payments = {}
payments_lock = Lock()


class PaymentRequest(BaseModel):
    order_id: int = Field(gt=0)
    user_id: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    simulate_failure: bool = False


class PaymentResponse(BaseModel):
    payment_id: str
    order_id: int
    user_id: str
    amount: Decimal
    status: str
    message: str


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "payment-service",
    }


@app.post("/payments", status_code=status.HTTP_201_CREATED)
def create_payment(request: PaymentRequest):
    payment_id = str(uuid4())

    payment_status = "failed" if request.simulate_failure else "succeeded"
    message = (
        "Simulated payment failure"
        if request.simulate_failure
        else "Simulated payment successful"
    )

    payment = {
        "payment_id": payment_id,
        "order_id": request.order_id,
        "user_id": request.user_id,
        "amount": request.amount,
        "status": payment_status,
        "message": message,
    }

    with payments_lock:
        payments[payment_id] = payment

    return payment


@app.get("/payments/{payment_id}")
def get_payment(payment_id: str):
    with payments_lock:
        payment = payments.get(payment_id)

    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    return payment
