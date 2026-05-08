import json
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Request, Depends

from src.controllers.stripe_controller import StripeController
from src.schemas.stripe_schema import GenerateCheckoutRequestSchema
from src.configs.db_connection import get_db

stripe_router = APIRouter()


@stripe_router.post("/generate")
async def generate_payment_checkout(
    body: GenerateCheckoutRequestSchema, db: AsyncSession = Depends(get_db)
):
    response = await StripeController.generate_payment_checkout(body.user_id, db)
    return response


@stripe_router.post("/webhook/payment")
async def payment_response_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    bytes_body = await request.body()
    request_body = json.loads(bytes_body.decode("utf-8"))

    response = await StripeController.payment_response_webhook(request_body, db)
    return response
