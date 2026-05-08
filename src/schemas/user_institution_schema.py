from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.schemas.institutions_schema import InstitutionBase
from src.schemas.profile_schemas import ProfileGet
from src.schemas.users_schemas import UsersLoginResponse


class UserInstitutionSchema(BaseModel):
    """Schema for user institution association."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": {"token": "token_jwt_aqui"}},
    )

    user_id: UUID
    institution_id: UUID
    profile_id: UUID
    created_at: datetime


class UserInstitutionSchemaJoin(BaseModel):
    """Schema for user institution association."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": {"token": "token_jwt_aqui"}},
    )

    user: UsersLoginResponse
    institution: InstitutionBase
    profile: ProfileGet
