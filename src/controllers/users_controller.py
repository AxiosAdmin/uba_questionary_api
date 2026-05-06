"""Controller for Users table"""

from fastapi import HTTPException
from api_crud_generate_libary.services.service import Service

from src.models import Users
from src.utils.fernet_utils import FernetUtils

fernet = FernetUtils()
generic_user_service = Service(Users)


class UsersController:
    """Controller class for handling user-related operations."""

    @staticmethod
    async def create_user(body, db):
        """Create a new user in the database after checking for nickname uniqueness."""
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
            if fernet.decrypt(user.nickname) == fernet.decrypt(body.nickname):
                raise HTTPException(status_code=400, detail="Nickname already exists")

        new_user = await generic_user_service.create(
            body.model_dump(),
            db,
            join_parameters=None,
            second_level_join_parameters=None,
        )

        return {"data": new_user}
