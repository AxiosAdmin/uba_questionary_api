"""Authentication controller handling login requests and token generation."""

from fastapi import HTTPException

from src.services.auth_service import AuthService
from src.services.subscription_service import SubscriptionService
from src.utils.jwt_utils import JWTUtils


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
