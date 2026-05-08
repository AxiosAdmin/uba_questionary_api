from typing import Optional

from pydantic import BaseModel

from src.schemas.user_institution_schema import UserInstitutionSchema
from src.schemas.users_schemas import UsersNoPasswordResponse


class QuestionGenerationUsageSchema(BaseModel):
    """Schema for monthly question generation usage."""

    questions_used: int
    questions_limit: Optional[int] = None
    questions_remaining: Optional[int] = None
    cycle_end: Optional[str] = None
    subscription_status: Optional[str] = None


class LoginSchema(BaseModel):
    """Schema for login credentials."""

    nickname: str
    password: str

    class Config:
        """Configure Pydantic to allow population from ORM objects and provide an example."""

        from_attributes = True
        json_schema_extra = {"example": {"nickname": "JokerVLP", "password": "123456"}}


class LoginResponseSchema(BaseModel):
    """Schema for login response with authenticated user data and JWT token."""

    user: UserInstitutionSchema
    token: str
    question_generation_usage: Optional[QuestionGenerationUsageSchema] = None

    class Config:
        """Configure Pydantic to allow population from ORM objects and provide an example."""

        from_attributes = True
        json_schema_extra = {
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
        }


class LoginAdminResponseSchema(BaseModel):
    """Schema for login response with authenticated user data and JWT token."""

    user: UsersNoPasswordResponse
    token: str
    question_generation_usage: Optional[QuestionGenerationUsageSchema] = None

    class Config:
        """Configure Pydantic to allow population from ORM objects and provide an example."""

        from_attributes = True
        json_schema_extra = {
            "example": {
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "John Doe",
                    "nickname": "johndoe",
                    "global_role": "admin",
                },
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }


class LoginUserResponseSchema(BaseModel):
    """Schema for login response with basic user data and JWT token."""

    user: UsersNoPasswordResponse
    token: str
    question_generation_usage: Optional[QuestionGenerationUsageSchema] = None

    class Config:
        """Configure Pydantic to allow population from ORM objects and provide an example."""

        from_attributes = True
        json_schema_extra = {
            "example": {
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "John Doe",
                    "nickname": "johndoe",
                    "global_role": "User",
                },
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }
