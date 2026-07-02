"""Authentication service for user validation."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from src.models import Users
from src.configs.configs import settings
from src.models.models import Subscriptions
from src.services.institutions_service import InstitutionsService
from src.services.user_institution_service import UserInstitutionService
from src.utils.fernet_utils import FernetUtils
from src.utils.jwt_utils import JWTUtils
from src.utils.password_utils import validate_password_requirements
from src.utils.user_lookup_utils import UserLookupUtils

fernet_utils = FernetUtils()
ACTIVE_SUBSCRIPTION_STATUSES = {"active"}


class AuthService:
    """Service for handling user authentication operations."""

    @staticmethod
    async def _find_user_by_email(email: str, db):
        email_hash = UserLookupUtils.hash_email(email)
        result = await db.execute(select(Users).where(Users.email_hash == email_hash))
        user = result.scalars().first()
        if user is not None:
            return user

        normalized_email = UserLookupUtils.normalize_email(email)
        result = await db.execute(select(Users).where(Users.email_hash.is_(None)))
        for user in result.scalars().all():
            if (
                UserLookupUtils.normalize_email(fernet_utils.decrypt(user.email))
                == normalized_email
            ):
                await AuthService._ensure_lookup_hashes(user, db)
                return user

        return None

    @staticmethod
    async def _find_user_by_nickname(nickname: str, db):
        nickname_hash = UserLookupUtils.hash_nickname(nickname)
        result = await db.execute(
            select(Users).where(Users.nickname_hash == nickname_hash)
        )
        user = result.scalars().first()
        if user is not None:
            return user

        normalized_nickname = UserLookupUtils.normalize_nickname(nickname)
        result = await db.execute(select(Users).where(Users.nickname_hash.is_(None)))
        for user in result.scalars().all():
            if (
                UserLookupUtils.normalize_nickname(fernet_utils.decrypt(user.nickname))
                == normalized_nickname
            ):
                await AuthService._ensure_lookup_hashes(user, db)
                return user

        return None

    @staticmethod
    async def _ensure_lookup_hashes(user, db):
        updated = False

        if getattr(user, "email_hash", None) is None:
            user.email_hash = UserLookupUtils.hash_email(fernet_utils.decrypt(user.email))
            updated = True

        if getattr(user, "nickname_hash", None) is None:
            user.nickname_hash = UserLookupUtils.hash_nickname(
                fernet_utils.decrypt(user.nickname)
            )
            updated = True

        if updated:
            await db.commit()

    @staticmethod
    async def _find_user_by_id(user_id, db):
        if not isinstance(user_id, UUID):
            user_id = UUID(str(user_id))

        result = await db.execute(select(Users).where(Users.id == user_id))
        return result.scalars().first()

    @staticmethod
    async def user_has_active_subscription(user_id, db):
        query = select(Subscriptions).where(
            Subscriptions.user_id == user_id,
            Subscriptions.status.in_(ACTIVE_SUBSCRIPTION_STATUSES),
        )

        result = await db.execute(query)
        subscription = result.scalars().first()

        return subscription is not None

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
        user = await AuthService._find_user_by_nickname(nickname, db)
        print(f"User found: {user.nickname if user else 'None'}")  # Debugging line
        if user and fernet_utils.decrypt(user.password) == password:
            if user.global_role == "Admin":
                return user

            uba_institution = await InstitutionsService.get_uba_institution(db)
            user_institutions = await UserInstitutionService.read_user_institutions(
                user.id, uba_institution.id, db
            )

            print(f"User institutions: {user_institutions}")  # Debugging line

            if user_institutions:
                return user_institutions

            return user

        raise ValueError("Invalid nickname or password")

    @staticmethod
    async def login_admin(nickname: str, password: str, db):
        """Authenticate a user and require the Admin global role."""
        user = await AuthService.login(nickname, password, db)

        if getattr(user, "global_role", None) != "Admin":
            raise PermissionError("Admin access is required")

        return user

    @staticmethod
    async def request_password_reset(email: str, db):
        """Generate a temporary password reset token for an existing user."""
        user = await AuthService._find_user_by_email(email, db)
        if user is None:
            return None

        return JWTUtils.encode_jwt(
            {
                "id": str(user.id),
                "sub": str(user.id),
                "purpose": "password_reset",
            },
            expires_in_minutes=settings.PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES,
        )

    @staticmethod
    async def reset_password(token: str, new_password: str, db):
        """Reset a user password using a valid password reset token."""
        payload = JWTUtils.decode_jwt(token)

        if payload.get("purpose") != "password_reset":
            raise ValueError("Invalid password reset token")

        user = await AuthService._find_user_by_id(payload.get("sub"), db)
        if user is None:
            raise ValueError("Invalid password reset token")

        validate_password_requirements(new_password)

        user.password = fernet_utils.encrypt(new_password)
        user.updated_at = datetime.now()
        await db.commit()

        return user
