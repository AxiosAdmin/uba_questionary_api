from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GenerateCheckoutRequestSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": {"user_id": "uuid aqui"}},
    )

    user_id: UUID
