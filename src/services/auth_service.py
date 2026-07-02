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
from src.utils.user_input_sanitizer import UserInputSanitizer
from src.utils.user_lookup_utils import UserLookupUtils

fernet_utils = FernetUtils()
ACTIVE_SUBSCRIPTION_STATUSES = {"active"}


class AuthService:
    """Service for handling user authentication operations."""

    @staticmethod
    async def _ensure_sanitized_user_fields(user, db):
        updated = False

        decrypted_email = fernet_utils.decrypt(user.email)
        sanitized_email = UserInputSanitizer.remove_all_spaces(decrypted_email)
        if decrypted_email != sanitized_email:
            user.email = fernet_utils.encrypt(sanitized_email)
            updated = True

        expected_email_hash = UserLookupUtils.hash_email(sanitized_email)
        if getattr(user, "email_hash", None) != expected_email_hash:
            user.email_hash = expected_email_hash
            updated = True

        decrypted_nickname = fernet_utils.decrypt(user.nickname)
        sanitized_nickname = UserInputSanitizer.remove_all_spaces(decrypted_nickname)
        if decrypted_nickname != sanitized_nickname:
            user.nickname = fernet_utils.encrypt(sanitized_nickname)
            updated = True

        expected_nickname_hash = UserLookupUtils.hash_nickname(sanitized_nickname)
        if getattr(user, "nickname_hash", None) != expected_nickname_hash:
            user.nickname_hash = expected_nickname_hash
            updated = True

        if updated:
            await db.commit()

        return user

    @staticmethod
    async def _find_user_by_email(email: str, db):
        email_hash = UserLookupUtils.hash_email(email)
        result = await db.execute(select(Users).where(Users.email_hash == email_hash))
        user = result.scalars().first()
        if user is not None:
            return await AuthService._ensure_sanitized_user_fields(user, db)

        normalized_email = UserLookupUtils.normalize_email(email)
        result = await db.execute(select(Users))
        for user in result.scalars().all():
            if (
                UserLookupUtils.normalize_email(fernet_utils.decrypt(user.email))
                == normalized_email
            ):
                return await AuthService._ensure_sanitized_user_fields(user, db)

        return None

    @staticmethod
    async def _find_user_by_nickname(nickname: str, db):
        nickname_hash = UserLookupUtils.hash_nickname(nickname)
        result = await db.execute(
            select(Users).where(Users.nickname_hash == nickname_hash)
        )
        user = result.scalars().first()
        if user is not None:
            return await AuthService._ensure_sanitized_user_fields(user, db)

        normalized_nickname = UserLookupUtils.normalize_nickname(nickname)
        result = await db.execute(select(Users))
        for user in result.scalars().all():
            if (
                UserLookupUtils.normalize_nickname(fernet_utils.decrypt(user.nickname))
                == normalized_nickname
            ):
                return await AuthService._ensure_sanitized_user_fields(user, db)

        return None

    @staticmethod
    async def _ensure_lookup_hashes(user, db):
        await AuthService._ensure_sanitized_user_fields(user, db)

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
        sanitized_password = UserInputSanitizer.remove_all_spaces(password)
        user = await AuthService._find_user_by_nickname(nickname, db)
        if (
            user
            and UserInputSanitizer.remove_all_spaces(fernet_utils.decrypt(user.password))
            == sanitized_password
        ):
            if user.global_role == "Admin":
                return user

            uba_institution = await InstitutionsService.get_uba_institution(db)
            user_institutions = await UserInstitutionService.read_user_institutions(
                user.id, uba_institution.id, db
            )

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
    async def request_nickname_recovery(email: str, db):
        """Generate a temporary nickname recovery token for an existing user."""
        user = await AuthService._find_user_by_email(email, db)
        if user is None:
            return None

        return JWTUtils.encode_jwt(
            {
                "id": str(user.id),
                "sub": str(user.id),
                "purpose": "nickname_recovery",
            },
            expires_in_minutes=settings.NICKNAME_RECOVERY_TOKEN_EXPIRATION_MINUTES,
        )

    @staticmethod
    async def reset_password(token: str, new_password: str, db):
        """Reset a user password using a valid password reset token."""
        sanitized_password = UserInputSanitizer.remove_all_spaces(new_password)
        payload = JWTUtils.decode_jwt(token)

        if payload.get("purpose") != "password_reset":
            raise ValueError("Invalid password reset token")

        user = await AuthService._find_user_by_id(payload.get("sub"), db)
        if user is None:
            raise ValueError("Invalid password reset token")

        validate_password_requirements(sanitized_password)

        user.password = fernet_utils.encrypt(sanitized_password)
        user.updated_at = datetime.now()
        await db.commit()

        return user

    @staticmethod
    async def recover_nickname(token: str, new_nickname: str, db):
        """Update a user nickname using a valid nickname recovery token."""
        sanitized_nickname = UserInputSanitizer.remove_all_spaces(new_nickname)
        payload = JWTUtils.decode_jwt(token)

        if payload.get("purpose") != "nickname_recovery":
            raise ValueError("Invalid nickname recovery token")

        user = await AuthService._find_user_by_id(payload.get("sub"), db)
        if user is None:
            raise ValueError("Invalid nickname recovery token")

        existing_user = await AuthService._find_user_by_nickname(sanitized_nickname, db)
        if existing_user is not None and existing_user.id != user.id:
            raise ValueError("Nickname already exists")

        user.nickname = fernet_utils.encrypt(sanitized_nickname)
        user.nickname_hash = UserLookupUtils.hash_nickname(sanitized_nickname)
        user.updated_at = datetime.now()
        await db.commit()

        return sanitized_nickname
