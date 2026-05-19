"""Pydantic schemas for question data validation and serialization."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class QuestionsBase(BaseModel):
    """Base schema for multiple-choice question data."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "question": "Qual é a capital do Brasil?",
                "answer_a": "São Paulo",
                "answer_b": "Rio de Janeiro",
                "answer_c": "Brasí­lia",
                "answer_d": "Belo Horizonte",
                "correct_answer": "C",
                "explanation_a": "São Paulo é a maior cidade, mas não a capital.",
                "explanation_b": "Rio de Janeiro foi a capital antiga.",
                "explanation_c": "Brasí­lia é a capital atual.",
                "explanation_d": "Belo Horizonte é uma cidade importante, mas não a capital.",
            }
        },
    )

    question: str
    answer_a: str
    answer_b: str
    answer_c: str
    answer_d: str
    correct_answer: str
    explanation_a: Optional[str] = None
    explanation_b: Optional[str] = None
    explanation_c: Optional[str] = None
    explanation_d: Optional[str] = None


class QuestionsGet(QuestionsBase):
    """Schema for retrieving question data with ID."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "question": "Qual é a capital do Brasil?",
                "answer_a": "São Paulo",
                "answer_b": "Rio de Janeiro",
                "answer_c": "Brasí­lia",
                "answer_d": "Belo Horizonte",
                "correct_answer": "C",
                "explanation_a": "São Paulo é a maior cidade, mas não a capital.",
                "explanation_b": "Rio de Janeiro foi a capital antiga.",
                "explanation_c": "Brasí­lia é a capital atual.",
                "explanation_d": "Belo Horizonte é uma cidade importante, mas não a capital.",
            }
        },
    )

    id: UUID
    institution_id: UUID
    topic: str
    subtopic: str
    subtopic_description: str
    diversity_mode: str


class OnlyQuestionsGetSchema(BaseModel):
    """Schema for retrieving question data without ID."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": {"question": "Qual é a capital do Brasil?"}},
    )

    question: str
