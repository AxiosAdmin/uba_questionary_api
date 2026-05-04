from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

from src.schemas.profile_schemas import ProfileGet
from src.utils.fernet_utils import FernetUtils


class UsersBase(BaseModel):
    """Base schema for user data with encrypted fields."""

    name: str
    nickname: str
    password: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "name": "Pedro Vieira Admin",
                "nickname": "JokerVLp",
                "password": "123456",
            }
        }


class UsersUpdate(BaseModel):
    """Schema for partial user updates with field encryption."""

    nickname: Optional[str] = None
    password: Optional[str] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {"nickname": "janedoe", "password": "newpassword456"}
        }

    @field_validator("nickname", "password", mode="before")
    @classmethod
    def encrypt_fields(cls, value: str) -> str:
        """
        Encrypt field value before saving to database.

        Args:
            value: The field value to encrypt

        Returns:
            str: Encrypted value
        """
        if not value:
            return value

        return FernetUtils().encrypt(value)


class UsersPost(UsersBase):
    """Schema for creating a new user with encrypted fields."""

    @field_validator("name", "nickname", "password", mode="before")
    @classmethod
    def encrypt_fields(cls, value: str) -> str:
        """
        Encrypt field value before saving to database.

        Args:
            value: The field value to encrypt

        Returns:
            str: Encrypted value
        """
        if not value:
            return value

        return FernetUtils().encrypt(value)


class UsersGet(UsersBase):
    """Schema for retrieving user data with decryption and profile relationship."""

    id: UUID
    profile: Optional[ProfileGet] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "nickname": "johndoe",
                "password": "securepassword123",
                "profile_id": "123e4567-e89b-12d3-a456-426614174000",
                "profile": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "Admin",
                    "counter_limit": 100,
                },
            }
        }

    @field_validator("nickname", "password", mode="after")
    @classmethod
    def decrypt_fields(cls, value: str) -> str:
        """
        Decrypt field value after loading from database.

        Args:
            value: The encrypted field value to decrypt

        Returns:
            str: Decrypted value or original value if decryption fails
        """
        if not value:
            return value
        try:
            return FernetUtils().decrypt(value)

        except Exception:  # pylint: disable=broad-exception-caught
            return value


class UsersNoPasswordResponse(BaseModel):
    """Schema for user response without password field."""

    id: UUID
    name: str
    nickname: str
    global_role: str

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "John Doe",
                "nickname": "johndoe",
            }
        }

    @field_validator("name", "nickname", mode="after")
    @classmethod
    def decrypt_fields(cls, value: str) -> str:
        """
        Decrypt nickname after loading from database.

        Args:
            value: The encrypted nickname to decrypt

        Returns:
            str: Decrypted nickname or original value if decryption fails
        """
        if not value:
            return value
        try:
            return FernetUtils().decrypt(value)

        except Exception:  # pylint: disable=broad-exception-caught
            return value


class UsersLoginResponse(BaseModel):
    """Schema dedicated to login responses with decrypted public user fields."""

    id: UUID
    name: str
    nickname: str

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "John Doe",
                "nickname": "johndoe",
            }
        }

    @field_validator("name", "nickname", mode="after")
    @classmethod
    def decrypt_fields(cls, value: str) -> str:
        """
        Decrypt login response fields loaded from the database.

        Args:
            value: The encrypted field value to decrypt

        Returns:
            str: Decrypted value or original value if decryption fails
        """
        if not value:
            return value
        try:
            return FernetUtils().decrypt(value)

        except Exception:  # pylint: disable=broad-exception-caught
            return value
