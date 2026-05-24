from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GenerateCheckoutRequestSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {"user_id": "uuid aqui", "coupon_code": "PROMO-UBA"}
        },
    )

    user_id: UUID
    coupon_code: str | None = None
