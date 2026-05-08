from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from src.utils.fernet_utils import FernetUtils


class UsersBase(BaseModel):
    """Base schema for user data with encrypted fields."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "name": "Pedro Vieira Admin",
                "email": "email@email.com",
                "nickname": "JokerVLp",
                "password": "123456",
            }
        },
    )

    name: str
    email: str
    nickname: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UsersPost(UsersBase):
    """Schema for creating a new user with encrypted fields."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "name": "Pedro Vieira",
                "email": "email@2mail.com",
                "nickname": "janedoe",
                "password": "newpassword456",
            }
        },
    )

    password: str

    @field_validator("name", "email", "nickname", "password", mode="before")
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

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "nickname": "johndoe",
                "password": "securepassword123",
                "profile_id": "123e4567-e89b-12d3-a456-426614174000",
            }
        },
    )

    id: UUID
    global_role: str

    @field_validator("name", "email", "nickname", mode="after")
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

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "John Doe",
                "nickname": "johndoe",
            }
        },
    )

    id: UUID
    name: str
    nickname: str
    global_role: str

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

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "John Doe",
                "nickname": "johndoe",
            }
        },
    )

    id: UUID
    name: str
    nickname: str

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
