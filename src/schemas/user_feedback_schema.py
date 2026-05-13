from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserFeedbackSchemaBase(BaseModel):
    """Base schema for user profile data."""

    id: Optional[UUID] = None
    user_id: UUID
    text_feedback: str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "uuid",
                "user_id": "uuid",
                "text_feedback": "Feedback construtivo que o usuário mandou",
            }
        },
    )
