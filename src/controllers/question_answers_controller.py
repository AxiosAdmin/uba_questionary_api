"""Question Answers Controller"""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from src.models import QuestionAnswers, Questions
from src.schemas.questions_answers_schema import (
    QuestionAnswersGet,
    QuestionAnswersPost,
)
from src.services.question_answers_service import QuestionAnswersService


class QuestionAnswersController:
    """Controller for handling question answer operations."""

    @staticmethod
    async def create_question_answer(
        current_user_id: UUID, body: QuestionAnswersPost, db
    ):
        """Persist a question answer for the authenticated user."""
        if not current_user_id:
            raise HTTPException(
                status_code=401,
                detail="Authenticated user is required to answer questions.",
            )

        question_exists = await db.scalar(
            select(Questions.id).where(Questions.id == body.question_id)
        )
        if question_exists is None:
            raise HTTPException(status_code=404, detail="Question not found")

        question_answer = QuestionAnswers(
            user_id=current_user_id,
            question_id=body.question_id,
            answer=body.answer,
        )
        db.add(question_answer)

        try:
            await db.commit()
            await db.refresh(question_answer)
        except SQLAlchemyError as exc:
            await db.rollback()
            raise HTTPException(
                status_code=503,
                detail=(
                    "Question answer persistence is temporarily unavailable. "
                    "Try again later."
                ),
            ) from exc

        return {"data": QuestionAnswersGet.model_validate(question_answer)}

    @staticmethod
    async def get_questions_with_latest_user_answers(
        user_id: UUID,
        db,
    ):
        """Return all questions with the latest answer sent by the given user, if any."""
        response = await QuestionAnswersService.get_questions_with_latest_user_answers(
            user_id,
            db,
        )
        return response
