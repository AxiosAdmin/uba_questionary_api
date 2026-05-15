from fastapi.responses import JSONResponse

from src.services.stripe_service import StripeService
from src.services.user_service import UserService


class StripeController:

    @staticmethod
    async def generate_payment_checkout(user_id, db):
        checkout_contact = await UserService.get_user_checkout_contact(user_id, db)

        if checkout_contact:
            response = StripeService.generate_payment_checkout(
                checkout_contact["id"],
                customer_email=checkout_contact["email"],
            )
            return response

        return JSONResponse(
            status_code=404,
            content={"message": "User doesn't exists"},
        )

    @staticmethod
    async def payment_response_webhook(request_data, db):
        event_handlers = {
            "checkout.session.completed": StripeService.checkout_session_completed,
            "checkout.session.async_payment_succeeded": (
                StripeService.checkout_session_async_payment_succeeded
            ),
            "checkout.session.async_payment_failed": (
                StripeService.checkout_session_async_payment_failed
            ),
            "charge.succeeded": StripeService.charge_succeeded,
            "charge.failed": StripeService.charge_failed,
            "charge.updated": StripeService.charge_updated,
            "charge.dispute.created": StripeService.charge_dispute_created,
            "charge.dispute.closed": StripeService.charge_dispute_closed,
            "radar.early_fraud_warning.created": (
                StripeService.radar_early_fraud_warning_created
            ),
        }

        event_handler = event_handlers.get(request_data["type"])
        if event_handler is None:
            return {"status": "ignored"}

        return await event_handler(request_data, db)
