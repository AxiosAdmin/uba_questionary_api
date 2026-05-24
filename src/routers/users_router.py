from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from api_crud_generate_libary.schemas.pattern_schema import PatternSchema

from src.controllers.users_controller import UsersController
from src.schemas.users_schemas import UsersGet, UsersPost, UsersProfileUpdate
from src.configs.db_connection import get_db

users_router = APIRouter()


@users_router.post("", response_model=PatternSchema[UsersGet])
async def create_user(body: UsersPost, db: AsyncSession = Depends(get_db)):
    """Endpoint to create a new user."""
    return await UsersController.create_user(body, db)


@users_router.get("/me", response_model=PatternSchema[UsersGet])
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    """Return the authenticated user profile."""
    return await UsersController.get_current_user(request.state.user_id, db)


@users_router.put("/me", response_model=PatternSchema[UsersGet])
async def update_current_user(
    body: UsersProfileUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Update the authenticated user profile."""
    return await UsersController.update_current_user(request.state.user_id, body, db)
