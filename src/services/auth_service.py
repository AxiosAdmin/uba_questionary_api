"""Authentication service for user validation."""

from sqlalchemy import select

from src.models import Users
from src.services.institutions_service import InstitutionsService
from src.services.user_institution_service import UserInstitutionService
from src.utils.fernet_utils import FernetUtils

fernet_utils = FernetUtils()


class AuthService:
    """Service for handling user authentication operations."""

    @staticmethod
    async def login(nickname: str, password: str, db):
        """
        Authenticate a user by nickname and password.

        Args:
            nickname: User's nickname for authentication
            password: User's password for authentication
            db: Database session for querying user data

        Returns:
            Users: User object if authentication succeeds

        Raises:
            ValueError: If nickname or password is invalid
        """
        query = select(Users)

        result = await db.execute(query)
        data = result.scalars().all()

        for user in data:
            if (
                fernet_utils.decrypt(user.nickname) == nickname
                and fernet_utils.decrypt(user.password) == password
            ):
                if user.global_role == "Admin":
                    return user

                uba_institution = await InstitutionsService.get_uba_institution(db)
                user_institutions = (
                    await UserInstitutionService.read_user_institutions(
                        user.id, uba_institution.id, db
                    )
                )

                return user_institutions

        raise ValueError("Invalid nickname or password")
