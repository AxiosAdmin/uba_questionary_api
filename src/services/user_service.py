from uuid import UUID
from sqlalchemy import select
from fastapi import HTTPException

from src.models import Users

class UserService:
    @staticmethod
    async def check_user_existance(user_id, db):
        if not isinstance(user_id, UUID):
            try:
                user_id = UUID(user_id)
            except ValueError as e:
                raise HTTPException(status_code=400, detail="Incorrect Id format") from e

        async with db as session:
            query = select(Users).where(Users.id == user_id)

            result = await session.execute(query)
            response = result.scalars().all()

            return True if len(response) > 0 else False
