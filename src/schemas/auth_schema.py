from typing import Optional

from pydantic import BaseModel, ConfigDict

from src.schemas.user_institution_schema import UserInstitutionSchemaJoin
from src.schemas.users_schemas import UsersNoPasswordResponse


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


class ForgotPasswordSchema(BaseModel):
    """Schema for requesting a password reset token."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "email@email.com"}}
    )

    email: str


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


class ForgotPasswordResponseSchema(BaseModel):
    """Generic response for password reset requests."""

    message: str
    reset_token: Optional[str] = None


class ResetPasswordResponseSchema(BaseModel):
    """Response for successful password reset."""

    message: str


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
