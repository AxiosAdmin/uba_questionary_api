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

        elif request_data["type"] == "checkout.session.async_payment_succeeded":
            response = await StripeService.checkout_session_async_payment_succeeded(
                request_data, db
            )

        elif request_data["type"] == "checkout.session.async_payment_failed":
            response = await StripeService.checkout_session_async_payment_failed(
                request_data, db
            )

        else:
            return {"status": "ignored"}

        return response
