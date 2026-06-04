"""Authentication router for login endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.controllers.auth_controller import AuthController
from src.schemas.auth_schema import (
    ForgotPasswordResponseSchema,
    ForgotPasswordSchema,
    LoginSchema,
    LoginResponseSchema,
    LoginAdminResponseSchema,
    LoginUserResponseSchema,
    ResetPasswordResponseSchema,
    ResetPasswordSchema,
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


@auth_router.post(
    "/login/admin",
    response_model=LoginAdminResponseSchema,
)
async def login_admin(body: LoginSchema, db: AsyncSession = Depends(get_db)):
    """Handle admin-only login requests."""
    response, token = await AuthController.login_admin(body.nickname, body.password, db)
    response["token"] = token
    return response


@auth_router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponseSchema,
)
async def forgot_password(
    body: ForgotPasswordSchema, db: AsyncSession = Depends(get_db)
):
    """Start the password reset flow for a given email."""
    return await AuthController.forgot_password(body.email, db)


@auth_router.post(
    "/reset-password",
    response_model=ResetPasswordResponseSchema,
)
async def reset_password(body: ResetPasswordSchema, db: AsyncSession = Depends(get_db)):
    """Reset the user password with a valid token."""
    return await AuthController.reset_password(body.token, body.new_password, db)
