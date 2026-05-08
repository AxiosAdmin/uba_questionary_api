import datetime
from uuid import UUID

from sqlalchemy import select
from stripe import StripeClient

from src.configs.configs import settings
from src.models.models import Institutions, Profiles, Subscriptions, UsersInstitutions

stripe_client = StripeClient(settings.SECRET_STRIPE_AUTH_KEY)

UBA_INSTITUTION_NAME = "UBA"
UBA_PROFILE_NAME = "basic_uba_user"
ACTIVE_ACCESS_STATUSES = {"active"}


class StripeService:
    @staticmethod
    def generate_payment_checkout(user_id):
        user_id_str = str(user_id)

        stripe_session = stripe_client.v1.checkout.sessions.create(
            {
                "mode": "subscription",
                "line_items": [{"price": settings.DEFAULT_PRICE_ID, "quantity": 1}],
                "currency": settings.PAYMENT_CURRENCY,
                "success_url": settings.CHECKOUT_REDIRECT_URL,
                "client_reference_id": user_id_str,
                "metadata": {
                    "user_id": user_id_str,
                    "price_id": settings.DEFAULT_PRICE_ID,
                },
                "subscription_data": {
                    "metadata": {
                        "user_id": user_id_str,
                        "price_id": settings.DEFAULT_PRICE_ID,
                    }
                },
            }
        )

        return {"url_session": stripe_session.url}

    @staticmethod
    def _normalize_subscription_status(stripe_status):
        normalized_status = {
            "active": "active",
            "trialing": "trialing",
            "incomplete": "incomplete",
            "incomplete_expired": "canceled",
            "past_due": "failed_payment",
            "unpaid": "failed_payment",
            "paused": "failed_payment",
            "canceled": "canceled",
        }

        return normalized_status.get(stripe_status, "incomplete")

    @staticmethod
    def _parse_uuid(user_id):
        if not user_id:
            return None

        if isinstance(user_id, UUID):
            return user_id

        try:
            return UUID(str(user_id))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _unix_to_datetime(timestamp_value):
        if not timestamp_value:
            return None

        return datetime.datetime.fromtimestamp(
            int(timestamp_value), tz=datetime.UTC
        ).replace(tzinfo=None)

    @staticmethod
    def _extract_user_id_from_metadata(payload):
        if not isinstance(payload, dict):
            return None

        metadata = payload.get("metadata") or {}
        if metadata.get("user_id"):
            return metadata["user_id"]

        subscription_details = payload.get("subscription_details") or {}
        subscription_metadata = subscription_details.get("metadata") or {}
        if subscription_metadata.get("user_id"):
            return subscription_metadata["user_id"]

        parent_details = payload.get("parent") or {}
        parent_subscription_details = parent_details.get("subscription_details") or {}
        parent_metadata = parent_subscription_details.get("metadata") or {}

        return parent_metadata.get("user_id")

    @staticmethod
    def _extract_price_id(payload):
        if not isinstance(payload, dict):
            return None

        metadata = payload.get("metadata") or {}
        if metadata.get("price_id"):
            return metadata["price_id"]

        items = payload.get("items", {}).get("data", [])
        if items:
            price = items[0].get("price") or {}
            if price.get("id"):
                return price["id"]

        lines = payload.get("lines", {}).get("data", [])
        if lines:
            price = lines[0].get("price") or {}
            if price.get("id"):
                return price["id"]

        subscription_details = payload.get("subscription_details") or {}
        if subscription_details.get("metadata", {}).get("price_id"):
            return subscription_details["metadata"]["price_id"]

        return None

    @staticmethod
    async def _get_uba_context(session):
        institution_query = select(Institutions).where(
            Institutions.name == UBA_INSTITUTION_NAME
        )
        profile_query = select(Profiles).where(Profiles.name == UBA_PROFILE_NAME)

        institution_result = await session.execute(institution_query)
        profile_result = await session.execute(profile_query)

        return (
            institution_result.scalars().first(),
            profile_result.scalars().first(),
        )

    @staticmethod
    async def _get_subscription_by_stripe_id(session, stripe_subscription_id):
        if not stripe_subscription_id:
            return None

        query = select(Subscriptions).where(
            Subscriptions.stripe_subscription_id == stripe_subscription_id
        )
        result = await session.execute(query)
        return result.scalars().first()

    @staticmethod
    async def _get_user_institution(session, user_id, institution_id):
        query = select(UsersInstitutions).where(
            UsersInstitutions.user_id == user_id,
            UsersInstitutions.institution_id == institution_id,
        )
        result = await session.execute(query)
        return result.scalars().first()

    @staticmethod
    async def _upsert_subscription(
        session,
        user_id,
        stripe_subscription_id,
        status,
        price_id,
        stripe_customer_id=None,
        current_period_end=None,
    ):
        subscription = await StripeService._get_subscription_by_stripe_id(
            session, stripe_subscription_id
        )

        if subscription:
            period_changed = (
                current_period_end is not None
                and subscription.current_period_end != current_period_end
            )
            subscription.user_id = user_id
            subscription.status = status
            subscription.price_id = price_id or subscription.price_id
            subscription.stripe_customer_id = (
                stripe_customer_id or subscription.stripe_customer_id
            )
            subscription.current_period_end = (
                current_period_end or subscription.current_period_end
            )
            if period_changed:
                subscription.questions_generated_in_cycle = 0
                subscription.questions_generation_cycle_end = current_period_end
            elif (
                subscription.questions_generation_cycle_end is None
                and subscription.current_period_end is not None
            ):
                subscription.questions_generation_cycle_end = (
                    subscription.current_period_end
                )
            subscription.updated_at = datetime.datetime.now(datetime.UTC).replace(
                tzinfo=None
            )
            return subscription, "updated"

        subscription = Subscriptions(
            user_id=user_id,
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=stripe_customer_id,
            status=status,
            price_id=price_id or settings.DEFAULT_PRICE_ID,
            current_period_end=current_period_end,
            questions_generated_in_cycle=0,
            questions_generation_cycle_end=current_period_end,
        )
        session.add(subscription)
        return subscription, "created"

    @staticmethod
    async def _grant_user_access(session, user_id, institution_id, profile_id):
        user_institution = await StripeService._get_user_institution(
            session, user_id, institution_id
        )

        if user_institution:
            if user_institution.profile_id != profile_id:
                user_institution.profile_id = profile_id
                user_institution.updated_at = datetime.datetime.now(
                    datetime.UTC
                ).replace(tzinfo=None)
                return "updated"

            return "unchanged"

        session.add(
            UsersInstitutions(
                user_id=user_id,
                institution_id=institution_id,
                profile_id=profile_id,
            )
        )
        return "created"

    @staticmethod
    async def _revoke_user_access(session, user_id, institution_id):
        user_institution = await StripeService._get_user_institution(
            session, user_id, institution_id
        )

        if not user_institution:
            return "unchanged"

        await session.delete(user_institution)
        return "deleted"

    @staticmethod
    async def _sync_user_access(session, user_id, normalized_status):
        institution, profile = await StripeService._get_uba_context(session)

        if not institution or not profile:
            raise ValueError(
                "The seed data for UBA institution/profile " \
                "must exist before processing Stripe webhooks."
            )

        if normalized_status in ACTIVE_ACCESS_STATUSES:
            access_action = await StripeService._grant_user_access(
                session, user_id, institution.id, profile.id
            )
        else:
            access_action = await StripeService._revoke_user_access(
                session, user_id, institution.id
            )

        return access_action

    @staticmethod
    async def _sync_subscription_from_subscription_event(data, db, forced_status=None):
        subscription_data = data["data"]["object"]
        stripe_subscription_id = subscription_data.get("id")

        async with db as session:
            existing_subscription = await StripeService._get_subscription_by_stripe_id(
                session, stripe_subscription_id
            )

            raw_user_id = StripeService._extract_user_id_from_metadata(
                subscription_data
            ) or (existing_subscription.user_id if existing_subscription else None)
            user_id = StripeService._parse_uuid(raw_user_id)

            if not user_id:
                return {
                    "status": "ignored",
                    "reason": "user_id_not_found",
                    "event": data["type"],
                }

            normalized_status = (
                forced_status
                or StripeService._normalize_subscription_status(
                    subscription_data.get("status")
                )
            )

            price_id = StripeService._extract_price_id(subscription_data)
            current_period_end = StripeService._unix_to_datetime(
                subscription_data.get("current_period_end")
            )
            stripe_customer_id = subscription_data.get("customer")

            subscription, operation = await StripeService._upsert_subscription(
                session=session,
                user_id=user_id,
                stripe_subscription_id=stripe_subscription_id,
                status=normalized_status,
                price_id=price_id,
                stripe_customer_id=stripe_customer_id,
                current_period_end=current_period_end,
            )
            access_action = await StripeService._sync_user_access(
                session, user_id, normalized_status
            )

            await session.commit()

            return {
                "status": "processed",
                "event": data["type"],
                "subscription_action": operation,
                "access_action": access_action,
                "stripe_subscription_id": subscription.stripe_subscription_id,
                "subscription_status": subscription.status,
            }

    @staticmethod
    async def checkout_session_completed(data, db):
        session_data = data["data"]["object"]
        user_id = StripeService._parse_uuid(
            StripeService._extract_user_id_from_metadata(session_data)
            or session_data.get("client_reference_id")
        )
        stripe_subscription_id = session_data.get("subscription")

        if not user_id:
            return {
                "status": "ignored",
                "reason": "user_id_not_found",
                "event": data["type"],
            }

        async with db as session:
            access_action = "unchanged"
            normalized_status = "incomplete"
            subscription_action = "unchanged"

            if stripe_subscription_id:
                existing_subscription = (
                    await StripeService._get_subscription_by_stripe_id(
                        session, stripe_subscription_id
                    )
                )

                if existing_subscription:
                    normalized_status = existing_subscription.status

                    if not existing_subscription.stripe_customer_id:
                        existing_subscription.stripe_customer_id = session_data.get(
                            "customer"
                        )

                    if not existing_subscription.price_id:
                        existing_subscription.price_id = (
                            StripeService._extract_price_id(session_data)
                            or settings.DEFAULT_PRICE_ID
                        )

                    existing_subscription.updated_at = datetime.datetime.now(
                        datetime.UTC
                    ).replace(tzinfo=None)
                    subscription_action = "updated"
                    access_action = await StripeService._sync_user_access(
                        session, user_id, normalized_status
                    )
                else:
                    _, subscription_action = await StripeService._upsert_subscription(
                        session=session,
                        user_id=user_id,
                        stripe_subscription_id=stripe_subscription_id,
                        status="incomplete",
                        price_id=StripeService._extract_price_id(session_data),
                        stripe_customer_id=session_data.get("customer"),
                        current_period_end=None,
                    )

            await session.commit()

            return {
                "status": "processed",
                "event": data["type"],
                "subscription_action": subscription_action,
                "access_action": access_action,
                "stripe_subscription_id": stripe_subscription_id,
                "subscription_status": normalized_status,
            }

    @staticmethod
    async def customer_subscription_created(data, db):
        return await StripeService._sync_subscription_from_subscription_event(data, db)

    @staticmethod
    async def customer_subscription_updated(data, db):
        return await StripeService._sync_subscription_from_subscription_event(data, db)

    @staticmethod
    async def customer_subscription_paused(data, db):
        return await StripeService._sync_subscription_from_subscription_event(
            data, db, forced_status="failed_payment"
        )

    @staticmethod
    async def customer_subscription_resumed(data, db):
        return await StripeService._sync_subscription_from_subscription_event(data, db)

    @staticmethod
    async def invoice_payment_succeeded(data, db):
        invoice_data = data["data"]["object"]
        stripe_subscription_id = invoice_data.get("subscription")

        if not stripe_subscription_id:
            return {
                "status": "ignored",
                "reason": "subscription_not_found",
                "event": data["type"],
            }

        async with db as session:
            existing_subscription = await StripeService._get_subscription_by_stripe_id(
                session, stripe_subscription_id
            )

            raw_user_id = StripeService._extract_user_id_from_metadata(
                invoice_data
            ) or (existing_subscription.user_id if existing_subscription else None)
            user_id = StripeService._parse_uuid(raw_user_id)

            if not user_id:
                return {
                    "status": "ignored",
                    "reason": "user_id_not_found",
                    "event": data["type"],
                }

            current_period_end = None
            lines = invoice_data.get("lines", {}).get("data", [])
            if lines:
                current_period_end = StripeService._unix_to_datetime(
                    lines[0].get("period", {}).get("end")
                )

            subscription, operation = await StripeService._upsert_subscription(
                session=session,
                user_id=user_id,
                stripe_subscription_id=stripe_subscription_id,
                status="active",
                price_id=StripeService._extract_price_id(invoice_data),
                stripe_customer_id=invoice_data.get("customer"),
                current_period_end=current_period_end,
            )
            access_action = await StripeService._sync_user_access(
                session, user_id, "active"
            )

            await session.commit()

            return {
                "status": "processed",
                "event": data["type"],
                "subscription_action": operation,
                "access_action": access_action,
                "stripe_subscription_id": subscription.stripe_subscription_id,
                "subscription_status": subscription.status,
            }

    @staticmethod
    async def invoice_paid(data, db):
        return await StripeService.invoice_payment_succeeded(data, db)

    @staticmethod
    async def invoice_payment_failed(data, db):
        invoice_data = data["data"]["object"]
        stripe_subscription_id = invoice_data.get("subscription")

        if not stripe_subscription_id:
            return {
                "status": "ignored",
                "reason": "subscription_not_found",
                "event": data["type"],
            }

        async with db as session:
            existing_subscription = await StripeService._get_subscription_by_stripe_id(
                session, stripe_subscription_id
            )

            raw_user_id = StripeService._extract_user_id_from_metadata(
                invoice_data
            ) or (existing_subscription.user_id if existing_subscription else None)
            user_id = StripeService._parse_uuid(raw_user_id)

            if not user_id:
                return {
                    "status": "ignored",
                    "reason": "user_id_not_found",
                    "event": data["type"],
                }

            normalized_status = "failed_payment"
            if invoice_data.get("billing_reason") == "subscription_create":
                normalized_status = "incomplete"

            subscription, operation = await StripeService._upsert_subscription(
                session=session,
                user_id=user_id,
                stripe_subscription_id=stripe_subscription_id,
                status=normalized_status,
                price_id=StripeService._extract_price_id(invoice_data),
                stripe_customer_id=invoice_data.get("customer"),
                current_period_end=(
                    existing_subscription.current_period_end
                    if existing_subscription
                    else None
                ),
            )
            access_action = await StripeService._sync_user_access(
                session, user_id, normalized_status
            )

            await session.commit()

            return {
                "status": "processed",
                "event": data["type"],
                "subscription_action": operation,
                "access_action": access_action,
                "stripe_subscription_id": subscription.stripe_subscription_id,
                "subscription_status": subscription.status,
            }

    @staticmethod
    async def customer_subscription_deleted(data, db):
        return await StripeService._sync_subscription_from_subscription_event(
            data, db, forced_status="canceled"
        )
