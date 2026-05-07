from fastapi.responses import JSONResponse

from src.services.stripe_service import StripeService
from src.services.user_service import UserService


class StripeController:

    @staticmethod
    async def generate_payment_checkout(user_id, db):
        user_exists = await UserService.check_user_existance(user_id, db)

        if user_exists:
            response = StripeService.generate_payment_checkout(user_id)
            return response

        return JSONResponse(
            status_code=404,
            content={"message": "User doesn't exists"},
        )

    @staticmethod
    async def payment_response_webhook(request_data, db):
        if request_data["type"] == "checkout.session.completed":
            response = await StripeService.checkout_session_completed(request_data, db)

        elif request_data["type"] == "customer.subscription.created":
            response = await StripeService.customer_subscription_created(request_data, db)

        elif request_data["type"] == "customer.subscription.updated":
            response = await StripeService.customer_subscription_updated(request_data, db)

        elif request_data["type"] == "customer.subscription.paused":
            response = await StripeService.customer_subscription_paused(request_data, db)

        elif request_data["type"] == "customer.subscription.resumed":
            response = await StripeService.customer_subscription_resumed(request_data, db)

        elif request_data["type"] == "invoice.paid":
            response = await StripeService.invoice_paid(request_data, db)

        elif request_data["type"] == "invoice.payment_succeeded":
            response = await StripeService.invoice_payment_succeeded(request_data, db)

        elif request_data["type"] == "invoice.payment_failed":
            response = await StripeService.invoice_payment_failed(request_data, db)

        elif request_data["type"] == "customer.subscription.deleted":
            response = await StripeService.customer_subscription_deleted(request_data, db)

        else:
            return {"status": "ignored"}

        return response
