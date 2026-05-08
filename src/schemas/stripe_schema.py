from uuid import UUID
from pydantic import BaseModel


class GenerateCheckoutRequestSchema(BaseModel):
    user_id: UUID

    class Config:
        """Configure Pydantic to allow population from ORM objects and provide an example."""

        from_attributes = True
        json_schema_extra = {"example": {"user_id": "uuid aqui"}}
