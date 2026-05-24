from uuid import UUID
from sqlalchemy import select
from fastapi import HTTPException

from src.models import Users
from src.utils.fernet_utils import FernetUtils

fernet_utils = FernetUtils()
MISSING_DNI_PLACEHOLDER = "00000000"


class UserService:
    @staticmethod
    def _parse_user_id(user_id):
        if isinstance(user_id, UUID):
            return user_id

        try:
            return UUID(str(user_id))
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Incorrect Id format") from e

    @staticmethod
    async def get_user_by_id(user_id, db):
        parsed_user_id = UserService._parse_user_id(user_id)

        async with db as session:
            query = select(Users).where(Users.id == parsed_user_id)
            result = await session.execute(query)
            return result.scalars().first()

    @staticmethod
    async def get_user_checkout_contact(user_id, db):
        user = await UserService.get_user_by_id(user_id, db)

        if user is None:
            return None

        response = {
            "id": user.id,
            "email": fernet_utils.decrypt(user.email).strip(),
        }

        if getattr(user, "dni", None):
            dni = fernet_utils.decrypt(user.dni).strip()
            response["has_pending_dni"] = dni == MISSING_DNI_PLACEHOLDER

        return response

    @staticmethod
    async def check_user_existance(user_id, db):
        user = await UserService.get_user_by_id(user_id, db)
        return user is not None
