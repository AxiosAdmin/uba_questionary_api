"""Pydantic schemas for question answers data validation and serialization."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

VALID_QUESTION_ANSWER_OPTIONS = {"A", "B", "C", "D", "E"}


class QuestionAnswersBase(BaseModel):
    """Base schema for question answer data."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "answer": "C",
                "question_id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
            }
        },
    )

    answer: str = Field(
        ...,
        min_length=1,
        max_length=1,
        description="User answer letter (A, B, C, D or E)",
    )
    question_id: Optional[UUID] = None
    user_id: Optional[UUID] = None

    @field_validator("answer")
    @classmethod
    def normalize_answer(cls, value: str) -> str:
        """Normalize answer letters and reject unsupported options."""
        normalized_value = value.strip().upper()
        if normalized_value not in VALID_QUESTION_ANSWER_OPTIONS:
            raise ValueError("answer must be one of: A, B, C, D, E")
        return normalized_value


class QuestionAnswersPost(QuestionAnswersBase):
    """Schema for creating a new question answer."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "answer": "B",
                "question_id": "123e4567-e89b-12d3-a456-426614174000",
            }
        },
    )

    question_id: UUID


class QuestionAnswersUpdate(BaseModel):
    """Schema for partial question answer updates."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": {"answer": "B"}},
    )

    answer: Optional[str] = Field(None, min_length=1, max_length=1)


class QuestionAnswersGet(QuestionAnswersBase):
    """Schema for retrieving question answer data with ID."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "answer": "C",
                "question_id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "created_at": "2024-01-15T10:30:00",
                "updated_at": None,
            }
        },
    )

    id: UUID
    question_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserQuestionWithLatestAnswerSchema(BaseModel):
    """Schema for returning all questions and the user's latest answer when it exists."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "institution_id": "123e4567-e89b-12d3-a456-426614174999",
                "topic": "Anatomia",
                "subject": "Sistema Nervoso",
                "question": "Qual estrutura forma o cerebelo?",
                "answer_a": "Opcao A",
                "answer_b": "Opcao B",
                "answer_c": "Opcao C",
                "answer_d": "Opcao D",
                "answer_e": None,
                "explanation_a": "Explicacao A",
                "explanation_b": "Explicacao B",
                "explanation_c": "Explicacao C",
                "explanation_d": "Explicacao D",
                "explanation_e": None,
                "correct_answer": "C",
                "created_at": "2024-01-15T10:30:00",
                "updated_at": None,
                "user_answer": "B",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "answered_at": "2024-01-20T14:00:00",
                "answer_updated_at": None,
            }
        },
    )

    id: UUID
    institution_id: UUID
    topic: str
    subject: str
    question: str
    answer_a: str
    answer_b: str
    answer_c: str
    answer_d: str
    answer_e: Optional[str] = None
    explanation_a: str
    explanation_b: str
    explanation_c: str
    explanation_d: str
    explanation_e: Optional[str] = None
    correct_answer: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    user_answer: str = ""
    user_id: Optional[UUID] = None
    answered_at: Optional[datetime] = None
    answer_updated_at: Optional[datetime] = None
