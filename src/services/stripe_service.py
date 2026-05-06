from stripe import StripeClient
from api_crud_generate_libary.services.service import Service

from src.services.profiles_service import ProfilesService
from src.services.institutions_service import InstitutionsService
from src.models import UsersInstitutions
from src.configs.configs import settings

stripe_client = StripeClient(settings.SECRET_STRIPE_AUTH_KEY)
generic_user_institution_service = Service(UsersInstitutions)


class StripeService:

    @staticmethod
    def generate_payment_checkout(user_id):
        stripe_session = stripe_client.v1.checkout.sessions.create(
            {
                "mode": "subscription",
                "line_items": [
                    {"price": "price_1TTnk4Q0ygO3vjZJGt8NL2I0", "quantity": 1}
                ],
                "currency": "USD",
                "success_url": "https://www.urlparaaguardarpagamento.com.br",
                "metadata": {
                    "user_id": user_id,
                },
            }
        )

        return {"url_session": stripe_session.url}

    @staticmethod
    async def checkout_session_completed(data, db):
        """
        Function gets the Webhook event that is sent when the checkout was finalized.
        The user insert the credit card and finished the operation, so it could be understood
        The user wants to sign the application and the profile could be related with the user
        """
        uba_institution = await InstitutionsService.get_uba_institution(db)
        uba_profile = await ProfilesService.get_uba_profile(db)
        user_id = data["data"]["object"]["metadata"]["user_id"]

        user_profile_institution = await generic_user_institution_service.create(
            {
                "user_id": user_id,
                "institution_id": uba_institution.id,
                "profile_id": uba_profile.id,
                "subscription_status": "pending",
            },
            db,
            join_parameters=None,
            second_level_join_parameters=None,
        )

        return user_profile_institution

    @staticmethod
    async def invoice_payment_succeeded(data, _db):
        """
        Function gets the Webhook event that is sent when the payment was succeeded.
        This fuction set the signature status as active.
        """

    @staticmethod
    async def invoice_payment_failed(data, _db):
        """
        Function gets the Webhook event that is sent when the payment was succeeded.
        This fuction set the signature status as inactive.
        """
        print("Invoice Payment Failed", data)

    @staticmethod
    async def customer_subscription_deleted(data, _db):
        """
        Function gets the Webhook event that is sent when the payment was succeeded.
        This fuction delete the user profile institution relation.
        """
        print("Customer Subscription Deleted", data)
