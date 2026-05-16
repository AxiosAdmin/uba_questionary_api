"""Authentication controller handling login requests and token generation."""

import logging

import jwt
from fastapi import HTTPException

from src.configs.configs import settings
from src.services.email_service import EmailService
from src.services.auth_service import AuthService
from src.services.subscription_service import SubscriptionService
from src.utils.jwt_utils import JWTUtils

logger = logging.getLogger(__name__)


class AuthController:
    """Controller for handling authentication-related operations."""

    @staticmethod
    async def login(nickname: str, password: str, db):
        """
        Process user login and generate JWT token.

        Args:
            nickname: User's nickname for authentication
            password: User's password for authentication
            db: Database session for querying user data

        Returns:
            tuple[dict, str]: Authenticated user data plus the generated JWT token
        """
        try:
            user = await AuthService.login(nickname, password, db)
            question_generation_usage = None

            if hasattr(user, "user") and user.user.id:
                question_generation_usage = (
                    await SubscriptionService.get_question_generation_usage(
                        user_id=user.user.id,
                        institution_id=user.institution_id,
                        db=db,
                    )
                )
                token_response = JWTUtils.encode_jwt(
                    {"id": str(user.user.id), "sub": str(user.user.id)}
                )

            else:
                if getattr(user, "global_role", None) != "Admin":
                    question_generation_usage = (
                        await SubscriptionService.get_question_generation_usage(
                            user_id=user.id,
                            institution_id=None,
                            db=db,
                        )
                    )
                token_response = JWTUtils.encode_jwt(
                    {"id": str(user.id), "sub": str(user.id)}
                )

            return {
                "user": user,
                "question_generation_usage": question_generation_usage,
            }, token_response

        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e)) from e

    @staticmethod
    async def forgot_password(email: str, db):
        """
        Start the password reset flow.

        Returns a generic success message regardless of whether the email exists,
        preventing account enumeration.
        """
        token = await AuthService.request_password_reset(email, db)
        if token is not None:
            try:
                EmailService.send_password_reset_email(email, token)
            except RuntimeError:
                logger.exception(
                    "Password reset email delivery failed for the forgot-password flow."
                )

        response = {
            "message": (
                "If the email exists, password reset instructions have been generated."
            )
        }

        if settings.PASSWORD_RESET_INCLUDE_TOKEN_IN_RESPONSE and token is not None:
            response["reset_token"] = token

        return response

    @staticmethod
    async def reset_password(token: str, new_password: str, db):
        """Validate a reset token and update the stored password."""
        try:
            await AuthService.reset_password(token, new_password, db)
            return {"message": "Password updated successfully."}
        except jwt.ExpiredSignatureError as exc:
            raise HTTPException(
                status_code=401, detail="Password reset token expired"
            ) from exc
        except jwt.InvalidTokenError as exc:
            raise HTTPException(
                status_code=400, detail="Invalid password reset token"
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
