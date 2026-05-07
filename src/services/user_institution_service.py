from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from fastapi import HTTPException

from src.models import UsersInstitutions


class UserInstitutionService:

    @staticmethod
    async def read_user_institutions(user_id, institution_id, db):
        try:
            user_uuid_id = user_id if isinstance(user_id, UUID) else UUID(user_id)
            institution_uuid_id = (
                institution_id
                if isinstance(institution_id, UUID)
                else UUID(institution_id)
            )
        except (TypeError, ValueError) as e:
            raise HTTPException(status_code=400, detail="Incorrect Id format") from e

        async with db as session:
            query = (
                select(UsersInstitutions)
                .where(
                    UsersInstitutions.user_id == user_uuid_id,
                    UsersInstitutions.institution_id == institution_uuid_id,
                )
                .options(
                    joinedload(UsersInstitutions.user),
                    joinedload(UsersInstitutions.institution),
                    joinedload(UsersInstitutions.profile),
                )
            )

            result = await session.execute(query)
            user_institutions = result.scalars().first()

            return user_institutions
