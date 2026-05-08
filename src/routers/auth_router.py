"""Authentication router for login endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.controllers.auth_controller import AuthController
from src.schemas.auth_schema import (
    LoginSchema,
    LoginResponseSchema,
    LoginAdminResponseSchema,
    LoginUserResponseSchema,
)
from src.configs.db_connection import get_db

auth_router = APIRouter()


@auth_router.post(
    "/login",
    response_model=LoginResponseSchema
    | LoginAdminResponseSchema
    | LoginUserResponseSchema,
)
async def login(body: LoginSchema, db: AsyncSession = Depends(get_db)):
    """
    Handle user login request.

    Args:
        body: Login credentials containing nickname and password
        db: Database session dependency

    Returns:
        LoginResponseSchema: User data and JWT token
    """
    response, token = await AuthController.login(body.nickname, body.password, db)
    response["token"] = token
    return response
