from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from src.schemas.user_institution_schema import UserInstitutionSchemaJoin
from src.schemas.users_schemas import UsersNoPasswordResponse
from src.utils.user_input_sanitizer import UserInputSanitizer


class QuestionGenerationUsageSchema(BaseModel):
    """Schema for purchased question package usage."""

    questions_used: int
    questions_limit: Optional[int] = None
    questions_remaining: Optional[int] = None
    cycle_end: Optional[str] = None
    subscription_status: Optional[str] = None


class LoginSchema(BaseModel):
    """Schema for login credentials."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": {"nickname": "JokerVLP", "password": "123456"}},
    )

    nickname: str
    password: str

    @field_validator("nickname", "password", mode="before")
    @classmethod
    def sanitize_login_fields(cls, value: str) -> str:
        return UserInputSanitizer.remove_all_spaces(value)


class ForgotPasswordSchema(BaseModel):
    """Schema for requesting a password reset token."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "email@email.com"}}
    )

    email: str

    @field_validator("email", mode="before")
    @classmethod
    def sanitize_email(cls, value: str) -> str:
        return UserInputSanitizer.remove_all_spaces(value)


class ForgotNicknameSchema(BaseModel):
    """Schema for requesting a nickname recovery token."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "email@email.com"}}
    )

    email: str

    @field_validator("email", mode="before")
    @classmethod
    def sanitize_email(cls, value: str) -> str:
        return UserInputSanitizer.remove_all_spaces(value)


class ResetPasswordSchema(BaseModel):
    """Schema for resetting password using a temporary token."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "new_password": "NovaSenha123!",
            }
        }
    )

    token: str
    new_password: str

    @field_validator("new_password", mode="before")
    @classmethod
    def sanitize_new_password(cls, value: str) -> str:
        return UserInputSanitizer.remove_all_spaces(value)


class RecoverNicknameSchema(BaseModel):
    """Schema for updating a nickname using a temporary token."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "new_nickname": "nuevo_nickname",
            }
        }
    )

    token: str
    new_nickname: str

    @field_validator("new_nickname", mode="before")
    @classmethod
    def validate_new_nickname(cls, value: str) -> str:
        normalized_value = UserInputSanitizer.remove_all_spaces(value)
        if not normalized_value:
            raise ValueError("New nickname is required")

        return normalized_value


class ForgotPasswordResponseSchema(BaseModel):
    """Generic response for password reset requests."""

    message: str
    reset_token: Optional[str] = None


class ForgotNicknameResponseSchema(BaseModel):
    """Generic response for nickname recovery requests."""

    message: str
    recovery_token: Optional[str] = None


class ResetPasswordResponseSchema(BaseModel):
    """Response for successful password reset."""

    message: str


class RecoverNicknameResponseSchema(BaseModel):
    """Response for successful nickname update."""

    message: str
    nickname: str


class LoginResponseSchema(BaseModel):
    """Schema for login response with authenticated user data and JWT token."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "user": {
                    "user": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "John Doe",
                        "nickname": "johndoe",
                    },
                    "institution": {
                        "id": "123e4567-e89b-12d3-a456-426614174001",
                        "name": "UBA",
                    },
                    "profile": {
                        "id": "123e4567-e89b-12d3-a456-426614174002",
                        "name": "Admin",
                    },
                },
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        },
    )

    user: UserInstitutionSchemaJoin
    token: str
    question_generation_usage: Optional[QuestionGenerationUsageSchema] = None


class LoginAdminResponseSchema(BaseModel):
    """Schema for login response with authenticated user data and JWT token."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "John Doe",
                    "nickname": "johndoe",
                    "global_role": "admin",
                },
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        },
    )

    user: UsersNoPasswordResponse
    token: str
    question_generation_usage: Optional[QuestionGenerationUsageSchema] = None


class LoginUserResponseSchema(BaseModel):
    """Schema for login response with basic user data and JWT token."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "John Doe",
                    "nickname": "johndoe",
                    "global_role": "User",
                },
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        },
    )

    user: UsersNoPasswordResponse
    token: str
    question_generation_usage: Optional[QuestionGenerationUsageSchema] = None
