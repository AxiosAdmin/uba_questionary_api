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
    def generate_payment_checkout(user_id, customer_email=None):
        user_id_str = str(user_id)
        metadata = {
            "user_id": user_id_str,
            "price_id": settings.DEFAULT_PRICE_ID,
        }
        stripe_payload = {
            "mode": "payment",
            "line_items": [{"price": settings.DEFAULT_PRICE_ID, "quantity": 1}],
            "adaptive_pricing": {"enabled": True},
            "billing_address_collection": "required",
            "customer_creation": "always",
            "invoice_creation": {"enabled": True},
            "locale": "es",
            "payment_method_options": {"card": {"request_three_d_secure": "automatic"}},
            "success_url": settings.CHECKOUT_REDIRECT_URL,
            "client_reference_id": user_id_str,
            "metadata": metadata,
            "payment_intent_data": {
                "metadata": metadata,
            },
        }

        if customer_email:
            stripe_payload["customer_email"] = customer_email
            stripe_payload["payment_intent_data"]["receipt_email"] = customer_email

        stripe_session = stripe_client.v1.checkout.sessions.create(stripe_payload)

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
    def _build_monitoring_response(data, category, action_required=False):
        object_data = data.get("data", {}).get("object", {})

        return {
            "status": "processed",
            "event": data["type"],
            "monitoring_category": category,
            "action_required": action_required,
            "object_id": object_data.get("id"),
            "object_type": object_data.get("object"),
            "charge_id": (
                object_data.get("charge")
                if object_data.get("object") != "charge"
                else object_data.get("id")
            ),
            "payment_intent_id": object_data.get("payment_intent"),
            "user_id": StripeService._extract_user_id_from_metadata(object_data),
            "price_id": StripeService._extract_price_id(object_data),
            "customer_email": (
                (object_data.get("billing_details") or {}).get("email")
                or object_data.get("receipt_email")
                or object_data.get("customer_email")
            ),
            "amount": object_data.get("amount"),
            "currency": object_data.get("currency"),
            "charge_status": object_data.get("status"),
        }

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
    async def _user_has_active_subscription(session, user_id):
        query = (
            select(Subscriptions)
            .where(
                Subscriptions.user_id == user_id,
                Subscriptions.status == "active",
            )
            .limit(1)
        )
        result = await session.execute(query)
        return result.scalars().first() is not None

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
            previous_period_end = getattr(subscription, "current_period_end", None)
            current_cycle_end = getattr(
                subscription, "questions_generation_cycle_end", None
            )
            period_changed = (
                current_period_end is not None
                and previous_period_end != current_period_end
            )
            subscription.stripe_subscription_id = stripe_subscription_id
            subscription.user_id = user_id
            subscription.status = status
            subscription.price_id = price_id or getattr(subscription, "price_id", None)
            subscription.stripe_customer_id = stripe_customer_id or getattr(
                subscription, "stripe_customer_id", None
            )
            subscription.current_period_end = (
                current_period_end
                if current_period_end is not None
                else previous_period_end
            )
            if period_changed:
                subscription.questions_generated_in_cycle = 0
                subscription.questions_generation_cycle_end = current_period_end
            elif (
                current_cycle_end is None
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
                "The seed data for UBA institution/profile "
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
    async def _sync_user_access_for_user(session, user_id):
        has_active_subscription = await StripeService._user_has_active_subscription(
            session, user_id
        )

        normalized_status = "active" if has_active_subscription else "canceled"
        return await StripeService._sync_user_access(
            session, user_id, normalized_status
        )

    @staticmethod
    async def _sync_checkout_session_purchase(data, db, normalized_status=None):
        session_data = data["data"]["object"]
        stripe_session_id = session_data.get("id")

        if not stripe_session_id:
            return {
                "status": "ignored",
                "reason": "checkout_session_not_found",
                "event": data["type"],
            }

        async with db as session:
            existing_subscription = await StripeService._get_subscription_by_stripe_id(
                session, stripe_session_id
            )

            raw_user_id = (
                StripeService._extract_user_id_from_metadata(session_data)
                or session_data.get("client_reference_id")
                or (existing_subscription.user_id if existing_subscription else None)
            )
            user_id = StripeService._parse_uuid(raw_user_id)

            if not user_id:
                return {
                    "status": "ignored",
                    "reason": "user_id_not_found",
                    "event": data["type"],
                }

            resolved_status = normalized_status
            if resolved_status is None:
                resolved_status = (
                    "active"
                    if session_data.get("payment_status") == "paid"
                    else "incomplete"
                )

            subscription, operation = await StripeService._upsert_subscription(
                session=session,
                user_id=user_id,
                stripe_subscription_id=stripe_session_id,
                status=resolved_status,
                price_id=StripeService._extract_price_id(session_data),
                stripe_customer_id=session_data.get("customer"),
                current_period_end=None,
            )
            access_action = await StripeService._sync_user_access_for_user(
                session, user_id
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
        return await StripeService._sync_checkout_session_purchase(data, db)

    @staticmethod
    async def checkout_session_async_payment_succeeded(data, db):
        return await StripeService._sync_checkout_session_purchase(
            data, db, normalized_status="active"
        )

    @staticmethod
    async def checkout_session_async_payment_failed(data, db):
        return await StripeService._sync_checkout_session_purchase(
            data, db, normalized_status="failed_payment"
        )

    @staticmethod
    async def charge_succeeded(data):
        return StripeService._build_monitoring_response(
            data, category="charge_succeeded"
        )

    @staticmethod
    async def charge_failed(data):
        return StripeService._build_monitoring_response(
            data,
            category="charge_failed",
            action_required=True,
        )

    @staticmethod
    async def charge_updated(data):
        return StripeService._build_monitoring_response(data, category="charge_updated")

    @staticmethod
    async def charge_dispute_created(data):
        return StripeService._build_monitoring_response(
            data,
            category="charge_dispute_created",
            action_required=True,
        )

    @staticmethod
    async def charge_dispute_closed(data):
        return StripeService._build_monitoring_response(
            data, category="charge_dispute_closed"
        )

    @staticmethod
    async def radar_early_fraud_warning_created(data):
        return StripeService._build_monitoring_response(
            data,
            category="early_fraud_warning",
            action_required=True,
        )

    @staticmethod
    async def customer_subscription_created(data):
        return {
            "status": "ignored",
            "reason": "unsupported_event",
            "event": data["type"],
        }

    @staticmethod
    async def customer_subscription_updated(data):
        return {
            "status": "ignored",
            "reason": "unsupported_event",
            "event": data["type"],
        }

    @staticmethod
    async def customer_subscription_paused(data):
        return {
            "status": "ignored",
            "reason": "unsupported_event",
            "event": data["type"],
        }

    @staticmethod
    async def customer_subscription_resumed(data):
        return {
            "status": "ignored",
            "reason": "unsupported_event",
            "event": data["type"],
        }

    @staticmethod
    async def invoice_payment_succeeded(data):
        return {
            "status": "ignored",
            "reason": "unsupported_event",
            "event": data["type"],
        }

    @staticmethod
    async def invoice_paid(data):
        return {
            "status": "ignored",
            "reason": "unsupported_event",
            "event": data["type"],
        }

    @staticmethod
    async def invoice_payment_failed(data):
        return {
            "status": "ignored",
            "reason": "unsupported_event",
            "event": data["type"],
        }

    @staticmethod
    async def customer_subscription_deleted(data):
        return {
            "status": "ignored",
            "reason": "unsupported_event",
            "event": data["type"],
        }
