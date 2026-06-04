"""Admin controller for manual outreach actions."""

import logging

from src.configs.configs import settings
from src.services.admin_service import AdminService
from src.services.email_service import EmailService

logger = logging.getLogger(__name__)


class AdminController:
    """Controller for secure admin-triggered campaigns."""

    @staticmethod
    async def get_user_payment_summary(current_user_id, db):
        """Return admin metrics for user registration/payment cohorts."""
        await AdminService.require_admin(current_user_id, db)
        return await AdminService.get_user_payment_summary(db)

    @staticmethod
    async def send_inactive_plan_email_campaign(current_user_id, body, db):
        """Preview or send the inactive-plan follow-up email campaign."""
        await AdminService.require_admin(current_user_id, db)
        recipients = await AdminService.get_inactive_plan_recipients(
            audience=body.audience,
            db=db,
            limit=body.limit,
        )

        sent_emails = 0
        failed_emails = 0

        if not body.dry_run:
            for recipient in recipients:
                try:
                    EmailService.send_inactive_plan_follow_up_email(
                        recipient=recipient["email"],
                        recipient_name=recipient["name"],
                        subject=body.subject,
                        body=body.message,
                    )
                    sent_emails += 1
                except RuntimeError:
                    failed_emails += 1
                    logger.exception(
                        "Inactive-plan follow-up email failed for user %s.",
                        recipient["user_id"],
                    )

        reply_to = settings.SUPPORT_EMAIL or settings.SMTP_FROM_EMAIL
        preview = recipients[:20]

        return {
            "message": (
                "Preview generated successfully."
                if body.dry_run
                else "Inactive-plan follow-up campaign processed."
            ),
            "audience": body.audience,
            "audience_label": AdminService.get_campaign_audience_label(body.audience),
            "dry_run": body.dry_run,
            "matched_users": len(recipients),
            "sent_emails": sent_emails,
            "failed_emails": failed_emails,
            "reply_to": reply_to,
            "recipients_preview": preview,
        }
