import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.models.models import Questions, Subscriptions, UsersInstitutions
from src.services.stripe_service import StripeService

ACTIVE_SUBSCRIPTION_STATUS = "active"
ACTIVE_SUBSCRIPTION_REQUIRED_DETAIL = "Active question package required."
QUESTIONS_PACKAGE_EXHAUSTED_DETAIL = (
    "Question package exhausted. Buy a new package to continue."
)


class SubscriptionService:
    @staticmethod
    def _parse_uuid(value, field_name):
        if isinstance(value, UUID):
            return value

        try:
            return UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid {field_name} format."
            ) from exc

    @staticmethod
    def _sync_generation_cycle(subscription):
        if not subscription.current_period_end:
            return

        if (
            subscription.questions_generation_cycle_end
            != subscription.current_period_end
        ):
            subscription.questions_generated_in_cycle = 0
            subscription.questions_generation_cycle_end = (
                subscription.current_period_end
            )
            subscription.updated_at = datetime.datetime.now(datetime.UTC).replace(
                tzinfo=None
            )

    @staticmethod
    async def _get_generation_context(user_id, institution_id, db, lock_subscription):
        user_uuid = SubscriptionService._parse_uuid(user_id, "user_id")
        institution_uuid = SubscriptionService._parse_uuid(
            institution_id, "institution_id"
        )

        user_institution_query = (
            select(UsersInstitutions)
            .where(
                UsersInstitutions.user_id == user_uuid,
                UsersInstitutions.institution_id == institution_uuid,
            )
            .options(joinedload(UsersInstitutions.profile))
        )
        user_institution_result = await db.execute(user_institution_query)
        user_institution = user_institution_result.scalars().first()

        if not user_institution or not user_institution.profile:
            raise HTTPException(
                status_code=403,
                detail="User does not have a valid profile for this institution.",
            )

        subscription_query = (
            select(Subscriptions)
            .where(
                Subscriptions.user_id == user_uuid,
                Subscriptions.status == ACTIVE_SUBSCRIPTION_STATUS,
            )
            .order_by(Subscriptions.created_at.asc())
            .limit(1)
        )

        if lock_subscription:
            subscription_query = subscription_query.with_for_update()

        subscription_result = await db.execute(subscription_query)
        subscription = subscription_result.scalars().first()

        if not subscription:
            raise HTTPException(
                status_code=403, detail=ACTIVE_SUBSCRIPTION_REQUIRED_DETAIL
            )

        return user_institution, subscription

    @staticmethod
    def _validate_generation_limit(subscription, questions_limit):
        used_questions = subscription.questions_generated_in_cycle or 0

        if questions_limit is not None and used_questions >= questions_limit:
            raise HTTPException(
                status_code=403,
                detail=QUESTIONS_PACKAGE_EXHAUSTED_DETAIL,
            )

    @staticmethod
    def _build_usage_summary(subscription, questions_limit):
        questions_used = (
            subscription.questions_generated_in_cycle if subscription else 0
        ) or 0
        questions_remaining = None

        if questions_limit is not None:
            questions_remaining = max(questions_limit - questions_used, 0)

        return {
            "questions_used": questions_used,
            "questions_limit": questions_limit,
            "questions_remaining": questions_remaining,
            "cycle_end": (
                subscription.questions_generation_cycle_end.isoformat()
                if subscription and subscription.questions_generation_cycle_end
                else None
            ),
            "subscription_status": subscription.status if subscription else None,
        }

    @staticmethod
    async def validate_question_generation_availability(user_id, institution_id, db):
        user_institution, subscription = (
            await SubscriptionService._get_generation_context(
                user_id=user_id,
                institution_id=institution_id,
                db=db,
                lock_subscription=False,
            )
        )

        SubscriptionService._sync_generation_cycle(subscription)
        SubscriptionService._validate_generation_limit(
            subscription, user_institution.profile.questions_create_limit
        )

        return SubscriptionService._build_usage_summary(
            subscription, user_institution.profile.questions_create_limit
        )

    @staticmethod
    async def get_question_generation_usage(user_id, institution_id, db):
        user_uuid = SubscriptionService._parse_uuid(user_id, "user_id")

        active_subscription_query = (
            select(Subscriptions)
            .where(
                Subscriptions.user_id == user_uuid,
                Subscriptions.status == ACTIVE_SUBSCRIPTION_STATUS,
            )
            .order_by(Subscriptions.created_at.asc())
            .limit(1)
        )
        active_subscription_result = await db.execute(active_subscription_query)
        subscription = active_subscription_result.scalars().first()

        if not subscription:
            subscription_query = (
                select(Subscriptions)
                .where(Subscriptions.user_id == user_uuid)
                .order_by(Subscriptions.created_at.desc())
                .limit(1)
            )
            subscription_result = await db.execute(subscription_query)
            subscription = subscription_result.scalars().first()

        questions_limit = None
        if institution_id:
            try:
                institution_uuid = SubscriptionService._parse_uuid(
                    institution_id, "institution_id"
                )
                user_institution_query = (
                    select(UsersInstitutions)
                    .where(
                        UsersInstitutions.user_id == user_uuid,
                        UsersInstitutions.institution_id == institution_uuid,
                    )
                    .options(joinedload(UsersInstitutions.profile))
                )
                user_institution_result = await db.execute(user_institution_query)
                user_institution = user_institution_result.scalars().first()
                if user_institution and user_institution.profile:
                    questions_limit = user_institution.profile.questions_create_limit
            except HTTPException:
                questions_limit = None

        if subscription:
            SubscriptionService._sync_generation_cycle(subscription)

        return SubscriptionService._build_usage_summary(subscription, questions_limit)

    @staticmethod
    async def _handle_exhausted_subscription(
        subscription, questions_limit, user_id, db
    ):
        if questions_limit is None:
            return

        used_questions = subscription.questions_generated_in_cycle or 0
        if used_questions < questions_limit:
            return

        subscription.status = "canceled"
        subscription.updated_at = datetime.datetime.now(datetime.UTC).replace(
            tzinfo=None
        )
        await StripeService._sync_user_access_for_user(db, user_id)

    @staticmethod
    async def create_question_and_consume_quota(
        user_id, institution_id, question_payload, db
    ):
        user_institution, subscription = (
            await SubscriptionService._get_generation_context(
                user_id=user_id,
                institution_id=institution_id,
                db=db,
                lock_subscription=True,
            )
        )

        SubscriptionService._sync_generation_cycle(subscription)
        SubscriptionService._validate_generation_limit(
            subscription, user_institution.profile.questions_create_limit
        )

        question = Questions(**question_payload)
        db.add(question)

        subscription.questions_generated_in_cycle = (
            subscription.questions_generated_in_cycle or 0
        ) + 1
        subscription.updated_at = datetime.datetime.now(datetime.UTC).replace(
            tzinfo=None
        )

        await SubscriptionService._handle_exhausted_subscription(
            subscription=subscription,
            questions_limit=user_institution.profile.questions_create_limit,
            user_id=user_id,
            db=db,
        )

        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        await db.refresh(question)
        return question, SubscriptionService._build_usage_summary(
            subscription, user_institution.profile.questions_create_limit
        )
