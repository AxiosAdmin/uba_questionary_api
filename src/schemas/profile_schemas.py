from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ProfileBase(BaseModel):
    """Base schema for user profile data."""

    name: str
    counter_limit: Optional[int] = None

    class Config:
        from_attributes = True
        json_schema_extra = {"example": {"name": "Admin", "counter_limit": 100}}


class ProfileUpdate(BaseModel):
    """Schema for partial profile updates."""

    name: Optional[str] = None
    counter_limit: Optional[int] = None

    class Config:
        from_attributes = True
        json_schema_extra = {"example": {"name": "User", "counter_limit": 50}}


class ProfilePost(ProfileBase):
    """Schema for creating a new profile."""

    pass


class ProfileGet(ProfileBase):
    """Schema for retrieving profile data with ID."""

    id: UUID

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Admin",
                "counter_limit": 100,
            }
        }
