"""Controller for Users table"""

import re

from fastapi import HTTPException
from api_crud_generate_libary.services.service import Service

from src.models import Users
from src.utils.fernet_utils import FernetUtils

fernet = FernetUtils()
generic_user_service = Service(Users)


class UsersController:
    """Controller class for handling user-related operations."""

    @staticmethod
    def _validate_password_requirements(encrypted_password: str) -> None:
        password = fernet.decrypt(encrypted_password)

        has_min_length = len(password) >= 8
        has_uppercase = bool(re.search(r"[A-Z]", password))
        has_lowercase = bool(re.search(r"[a-z]", password))
        has_number = bool(re.search(r"\d", password))
        has_special_character = bool(re.search(r"[^A-Za-z0-9]", password))

        if not all(
            [
                has_min_length,
                has_uppercase,
                has_lowercase,
                has_number,
                has_special_character,
            ]
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Password must be at least 8 characters long and contain at "
                    "least one uppercase letter, one lowercase letter, one number, "
                    "and one special character"
                ),
            )

    @staticmethod
    async def create_user(body, db):
        """Create a new user in the database after checking for nickname uniqueness."""
        UsersController._validate_password_requirements(body.password)

        users = await generic_user_service.read(
            db,
            join_parameters=None,
            second_level_join_parameters=None,
            page=None,
            items_per_page=None,
            order_by=None,
            direction=None,
        )

        for user in users[0]:
            if fernet.decrypt(user.nickname) == fernet.decrypt(
                body.nickname
            ) or fernet.decrypt(user.email) == fernet.decrypt(body.email):
                raise HTTPException(status_code=400, detail="Nickname or Email already exists")

        new_user = await generic_user_service.create(
            body.model_dump(),
            db,
            join_parameters=None,
            second_level_join_parameters=None,
        )

        return {"data": new_user}
