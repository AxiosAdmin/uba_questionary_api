from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Request, Depends, Header, HTTPException
import stripe

from src.controllers.stripe_controller import StripeController
from src.schemas.stripe_schema import GenerateCheckoutRequestSchema
from src.configs.configs import settings
from src.configs.db_connection import get_db

stripe_router = APIRouter()


@stripe_router.post("/generate")
async def generate_payment_checkout(
    body: GenerateCheckoutRequestSchema, db: AsyncSession = Depends(get_db)
):
    response = await StripeController.generate_payment_checkout(body.user_id, db)
    return response


@stripe_router.post("/webhook/payment")
async def payment_response_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    stripe_signature: str | None = Header(default=None, alias="stripe-signature"),
):
    bytes_body = await request.body()

    try:
        request_body = stripe.Webhook.construct_event(
            payload=bytes_body,
            sig_header=stripe_signature or "",
            secret=settings.WEBHOOK_STRIPE_SECRECT_KEY,
        )
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise HTTPException(
            status_code=400, detail="Invalid Stripe webhook signature"
        ) from exc

    response = await StripeController.payment_response_webhook(request_body, db)
    return response
