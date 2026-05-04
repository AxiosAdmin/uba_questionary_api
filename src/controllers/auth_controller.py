"""Authentication controller handling login requests and token generation."""

from fastapi import HTTPException

from src.services.auth_service import AuthService
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

            if hasattr(user, "user") and user.user.id:
                token_response = JWTUtils.encode_jwt(
                    {"id": str(user.user.id), "sub": str(user.user.id)}
                )

            else:
                token_response = JWTUtils.encode_jwt(
                    {"id": str(user.id), "sub": str(user.id)}
                )

            return {"user": user}, token_response

        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e)) from e
