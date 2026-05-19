"""Router for AI biology question generation endpoints."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from api_crud_generate_libary.schemas.pattern_schema import PatternSchema

from src.controllers.ai_biology_controller import AIBiologyController
from src.schemas.ai_biology_schemas import BiologySchema
from src.schemas import QuestionsGet
from src.configs.db_connection import get_db

ai_biology_router = APIRouter()


@ai_biology_router.post("/biology", response_model=PatternSchema[QuestionsGet])
async def generate_question(
    request: Request, data: BiologySchema, db: AsyncSession = Depends(get_db)
):
    """
    Generate a biology question using AI.

    Args:
        request: FastAPI request object
        data: BiologySchema containing the topic parameter
        db: Database session

    Returns:
        dict: Generated question in JSON format
    """
    institution_id = request.headers.get("x-institution-id")
    user_id = getattr(request.state, "user_id", None)
    response = await AIBiologyController.generate_question(
        data.parameter, db, institution_id, user_id
    )
    return response
