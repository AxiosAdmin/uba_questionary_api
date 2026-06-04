"""Schemas for admin-triggered outreach campaigns."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CampaignAudience = Literal[
    "never_paid",
    "paid_without_active_subscription",
]


class InactivePlanEmailCampaignSchema(BaseModel):
    """Payload for manually triggering the inactive-plan outreach email."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "audience": "never_paid",
                "subject": "Sentimos sua falta na Axios Academia",
                "message": (
                    "Percebemos que voce esta sem plano ativo no momento.\n\n"
                    "Queria entender se esta faltando alguma funcionalidade, "
                    "conteudo ou ajuste para que a plataforma faca mais sentido "
                    "para voce.\n\n"
                    "Se quiser, e so responder este email."
                ),
                "dry_run": True,
                "confirm_send": False,
                "limit": 50,
            }
        }
    )

    audience: CampaignAudience
    subject: str = Field(min_length=3, max_length=160)
    message: str = Field(min_length=10, max_length=5000)
    dry_run: bool = True
    confirm_send: bool = False
    limit: int | None = Field(default=None, ge=1, le=1000)

    @model_validator(mode="after")
    def validate_confirmation(self):
        """Require an explicit confirmation flag before any real delivery."""
        if not self.dry_run and not self.confirm_send:
            raise ValueError("confirm_send must be true when dry_run is false.")

        return self


class InactivePlanEmailRecipientPreviewSchema(BaseModel):
    """Preview of users matched by the inactive-plan campaign."""

    user_id: str
    name: str | None = None
    email: str


class InactivePlanEmailCampaignResponseSchema(BaseModel):
    """Structured response for the inactive-plan campaign trigger."""

    message: str
    audience: CampaignAudience
    audience_label: str
    dry_run: bool
    matched_users: int
    sent_emails: int
    failed_emails: int
    reply_to: str
    recipients_preview: list[InactivePlanEmailRecipientPreviewSchema] = Field(
        default_factory=list
    )


class AdminUserPaymentSummarySchema(BaseModel):
    """Aggregate admin view of registration and payment status."""

    total_registered_users: int
    never_paid_users: int
    paid_without_active_subscription_users: int
    active_subscription_users: int
    users_without_active_subscription: int
