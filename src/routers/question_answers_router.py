from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api_crud_generate_libary.schemas.pattern_schema import PatternSchemaDataList
from uuid import UUID

from src.configs.db_connection import get_db
from src.controllers.question_answers_controller import QuestionAnswersController
from src.schemas.questions_answers_schema import UserQuestionWithLatestAnswerSchema

question_answers_router = APIRouter()


@question_answers_router.get(
    "/latest-answers",
    response_model=PatternSchemaDataList[UserQuestionWithLatestAnswerSchema],
)
async def get_questions_with_latest_user_answers(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Return all questions with the latest answer sent by the given user, if any.

    Args:
        user_id: The ID of the user to filter answers by
        db: Database session dependency

    Returns:
        A list of questions with the latest answer from the specified user, if any.
    """
    response = await QuestionAnswersController.get_questions_with_latest_user_answers(
        user_id,
        db,
    )
    return response
