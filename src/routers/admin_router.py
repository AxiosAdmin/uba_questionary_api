"""Admin routes for manual operational actions."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.configs.db_connection import get_db
from src.controllers.admin_controller import AdminController
from src.schemas.admin_schema import (
    AdminUserPaymentSummarySchema,
    InactivePlanEmailCampaignResponseSchema,
    InactivePlanEmailCampaignSchema,
)

admin_router = APIRouter()


@admin_router.get(
    "/dashboard/user-payment-summary",
    response_model=AdminUserPaymentSummarySchema,
)
async def get_user_payment_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Return admin summary counts for user payment cohorts."""
    return await AdminController.get_user_payment_summary(
        current_user_id=request.state.user_id,
        db=db,
    )


@admin_router.post(
    "/email-campaigns/inactive-plan-follow-up",
    response_model=InactivePlanEmailCampaignResponseSchema,
)
async def send_inactive_plan_follow_up_email_campaign(
    body: InactivePlanEmailCampaignSchema,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Preview or send a manual inactive-plan follow-up email campaign."""
    return await AdminController.send_inactive_plan_email_campaign(
        current_user_id=request.state.user_id,
        body=body,
        db=db,
    )
