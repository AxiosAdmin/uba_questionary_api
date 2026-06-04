"""Admin-only services for manual outreach operations."""

from sqlalchemy import exists, func, select
from fastapi import HTTPException

from src.models import Users
from src.models.models import Subscriptions
from src.services.auth_service import ACTIVE_SUBSCRIPTION_STATUSES, AuthService
from src.utils.fernet_utils import FernetUtils

fernet_utils = FernetUtils()
CAMPAIGN_AUDIENCE_LABELS = {
    "never_paid": "Usuarios que nunca pagaram",
    "paid_without_active_subscription": (
        "Usuarios que ja pagaram, mas nao possuem pagamento ativo"
    ),
}


class AdminService:
    """Service layer for admin-triggered manual campaigns."""

    @staticmethod
    def _base_non_admin_users_query():
        """Return the shared base query for non-admin users."""
        return select(Users).where(Users.global_role != "Admin")

    @staticmethod
    def _subscription_status_exists():
        """Return correlated subscription predicates reused by admin reports."""
        active_subscription_exists = exists(
            select(1).where(
                Subscriptions.user_id == Users.id,
                Subscriptions.status.in_(ACTIVE_SUBSCRIPTION_STATUSES),
            )
        )
        any_subscription_exists = exists(
            select(1).where(Subscriptions.user_id == Users.id)
        )
        return active_subscription_exists, any_subscription_exists

    @staticmethod
    def get_campaign_audience_label(audience: str) -> str:
        """Return the user-facing label for a campaign audience."""
        return CAMPAIGN_AUDIENCE_LABELS.get(audience, audience)

    @staticmethod
    async def require_admin(user_id, db):
        """Ensure the authenticated user exists and has the Admin global role."""
        user = await AuthService._find_user_by_id(user_id, db)
        if user is None:
            raise HTTPException(status_code=404, detail="Authenticated user not found.")

        if getattr(user, "global_role", None) != "Admin":
            raise HTTPException(status_code=403, detail="Admin access is required.")

        return user

    @staticmethod
    async def get_inactive_plan_recipients(
        audience: str,
        db,
        limit: int | None = None,
    ):
        """Return recipients for a selected outreach audience."""
        active_subscription_exists, any_subscription_exists = (
            AdminService._subscription_status_exists()
        )

        query = AdminService._base_non_admin_users_query()

        if audience == "never_paid":
            query = query.where(~any_subscription_exists)
        elif audience == "paid_without_active_subscription":
            query = query.where(any_subscription_exists, ~active_subscription_exists)
        else:
            raise HTTPException(status_code=400, detail="Invalid campaign audience.")

        query = query.order_by(Users.created_at.asc())

        if limit is not None:
            query = query.limit(limit)

        result = await db.execute(query)
        users = result.scalars().all()

        recipients = []
        for user in users:
            recipients.append(
                {
                    "user_id": str(user.id),
                    "name": fernet_utils.decrypt(user.name).strip(),
                    "email": fernet_utils.decrypt(user.email).strip(),
                }
            )

        return recipients

    @staticmethod
    async def get_user_payment_summary(db):
        """Return aggregate counts for registration/payment cohorts."""
        active_subscription_exists, any_subscription_exists = (
            AdminService._subscription_status_exists()
        )

        total_registered_users = await db.scalar(
            select(func.count())
            .select_from(Users)
            .where(Users.global_role != "Admin")
        )
        never_paid_users = await db.scalar(
            select(func.count())
            .select_from(Users)
            .where(
                Users.global_role != "Admin",
                ~any_subscription_exists,
            )
        )
        paid_without_active_subscription_users = await db.scalar(
            select(func.count())
            .select_from(Users)
            .where(
                Users.global_role != "Admin",
                any_subscription_exists,
                ~active_subscription_exists,
            )
        )
        active_subscription_users = await db.scalar(
            select(func.count())
            .select_from(Users)
            .where(
                Users.global_role != "Admin",
                active_subscription_exists,
            )
        )

        return {
            "total_registered_users": total_registered_users or 0,
            "never_paid_users": never_paid_users or 0,
            "paid_without_active_subscription_users": (
                paid_without_active_subscription_users or 0
            ),
            "active_subscription_users": active_subscription_users or 0,
            "users_without_active_subscription": (
                (never_paid_users or 0)
                + (paid_without_active_subscription_users or 0)
            ),
        }
