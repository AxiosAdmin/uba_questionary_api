from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.models import UsersInstitutions


class UserInstitutionsService:
    @staticmethod
    async def read_user_institutions(user_id, institution_id, db):
        async with db as session:
            query = (
                select(UsersInstitutions)
                .where(
                    UsersInstitutions.user_id == user_id
                    and UsersInstitutions.institution_id == institution_id
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
