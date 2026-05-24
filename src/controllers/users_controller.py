"""Controller for Users table"""

from datetime import datetime

from fastapi import HTTPException
from api_crud_generate_libary.services.service import Service
from sqlalchemy import or_, select

from src.models import Users
from src.utils.cbu_utils import CbuUtils
from src.utils.fernet_utils import FernetUtils
from src.utils.password_utils import (
    PASSWORD_REQUIREMENTS_MESSAGE,
    validate_password_requirements,
)
from src.utils.user_lookup_utils import UserLookupUtils

fernet = FernetUtils()
generic_user_service = Service(Users)
DUPLICATE_USER_DETAIL = "Nickname, Email or CBU already exists"
CBU_UPDATE_FORBIDDEN_DETAIL = (
    "CBU can only be updated for users pending CBU registration"
)
MISSING_CBU_PLACEHOLDER = "0000000000000000000000"


class UsersController:
    """Controller class for handling user-related operations."""

    @staticmethod
    def _validate_password_requirements(encrypted_password: str) -> None:
        try:
            validate_password_requirements(fernet.decrypt(encrypted_password))
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=PASSWORD_REQUIREMENTS_MESSAGE,
            ) from exc

    @staticmethod
    def _validate_cbu(encrypted_cbu: str) -> str:
        try:
            return CbuUtils.normalize_and_validate(fernet.decrypt(encrypted_cbu))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="CBU is invalid") from exc

    @staticmethod
    async def _find_user_by_cbu_hash(cbu_hash: str, db):
        result = await db.execute(select(Users).where(Users.cbu_hash == cbu_hash))
        return result.scalars().first()

    @staticmethod
    async def _find_user_by_email_hash(email_hash: str, db):
        result = await db.execute(select(Users).where(Users.email_hash == email_hash))
        return result.scalars().first()

    @staticmethod
    async def _find_user_by_nickname_hash(nickname_hash: str, db):
        result = await db.execute(
            select(Users).where(Users.nickname_hash == nickname_hash)
        )
        return result.scalars().first()

    @staticmethod
    async def _find_legacy_duplicate_user(
        email: str, nickname: str, db, exclude_user_id=None
    ):
        result = await db.execute(
            select(Users).where(
                or_(Users.email_hash.is_(None), Users.nickname_hash.is_(None))
            )
        )
        legacy_users = result.scalars().all()
        normalized_email = UserLookupUtils.normalize_email(email)
        normalized_nickname = UserLookupUtils.normalize_nickname(nickname)

        for user in legacy_users:
            if exclude_user_id is not None and user.id == exclude_user_id:
                continue

            if (
                UserLookupUtils.normalize_email(fernet.decrypt(user.email))
                == normalized_email
                or UserLookupUtils.normalize_nickname(fernet.decrypt(user.nickname))
                == normalized_nickname
            ):
                return user

        return None

    @staticmethod
    async def _get_user_or_404(user_id, db):
        result = await db.execute(select(Users).where(Users.id == user_id))
        user = result.scalars().first()

        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        return user

    @staticmethod
    def _get_stored_cbu_value(user) -> str:
        raw_cbu = getattr(user, "cbu", None)
        if not raw_cbu:
            return ""

        try:
            return fernet.decrypt(raw_cbu)
        except Exception:  # pylint: disable=broad-exception-caught
            return raw_cbu

    @staticmethod
    async def _validate_unique_profile_fields(
        current_user_id, plain_email, plain_nickname, cbu_hash, db
    ):
        email_hash = UserLookupUtils.hash_email(plain_email)
        nickname_hash = UserLookupUtils.hash_nickname(plain_nickname)

        existing_email_user = await UsersController._find_user_by_email_hash(
            email_hash, db
        )
        if existing_email_user is not None and existing_email_user.id != current_user_id:
            raise HTTPException(status_code=400, detail=DUPLICATE_USER_DETAIL)

        existing_nickname_user = await UsersController._find_user_by_nickname_hash(
            nickname_hash, db
        )
        if (
            existing_nickname_user is not None
            and existing_nickname_user.id != current_user_id
        ):
            raise HTTPException(status_code=400, detail=DUPLICATE_USER_DETAIL)

        existing_cbu_user = await UsersController._find_user_by_cbu_hash(cbu_hash, db)
        if existing_cbu_user is not None and existing_cbu_user.id != current_user_id:
            raise HTTPException(status_code=400, detail=DUPLICATE_USER_DETAIL)

        legacy_duplicate_user = await UsersController._find_legacy_duplicate_user(
            plain_email,
            plain_nickname,
            db,
            exclude_user_id=current_user_id,
        )
        if legacy_duplicate_user is not None:
            raise HTTPException(status_code=400, detail=DUPLICATE_USER_DETAIL)

        return email_hash, nickname_hash

    @staticmethod
    async def create_user(body, db):
        """Create a new user in the database after checking for nickname uniqueness."""
        UsersController._validate_password_requirements(body.password)
        normalized_cbu = UsersController._validate_cbu(body.cbu)
        cbu_hash = CbuUtils.hash_normalized(normalized_cbu)
        plain_email = fernet.decrypt(body.email)
        plain_nickname = fernet.decrypt(body.nickname)
        email_hash, nickname_hash = await UsersController._validate_unique_profile_fields(
            None,
            plain_email,
            plain_nickname,
            cbu_hash,
            db,
        )

        new_user_payload = body.model_dump()
        new_user_payload["email_hash"] = email_hash
        new_user_payload["nickname_hash"] = nickname_hash
        new_user_payload["cbu_hash"] = cbu_hash
        new_user = await generic_user_service.create(
            new_user_payload,
            db,
            join_parameters=None,
            second_level_join_parameters=None,
        )

        return {"data": new_user}

    @staticmethod
    async def get_current_user(user_id, db):
        """Return the authenticated user profile."""
        user = await UsersController._get_user_or_404(user_id, db)
        return {"data": user}

    @staticmethod
    async def update_current_user(user_id, body, db):
        """Update the authenticated user's public profile fields."""
        user = await UsersController._get_user_or_404(user_id, db)
        current_cbu = UsersController._get_stored_cbu_value(user)
        normalized_cbu = UsersController._validate_cbu(body.cbu)
        if current_cbu != MISSING_CBU_PLACEHOLDER:
            current_normalized_cbu = CbuUtils.normalize(current_cbu)
            if normalized_cbu != current_normalized_cbu:
                raise HTTPException(
                    status_code=400,
                    detail=CBU_UPDATE_FORBIDDEN_DETAIL,
                )

        cbu_hash = CbuUtils.hash_normalized(normalized_cbu)
        plain_email = fernet.decrypt(body.email)
        plain_nickname = fernet.decrypt(body.nickname)
        email_hash, nickname_hash = await UsersController._validate_unique_profile_fields(
            user.id,
            plain_email,
            plain_nickname,
            cbu_hash,
            db,
        )

        user.name = body.name
        user.email = body.email
        user.email_hash = email_hash
        user.nickname = body.nickname
        user.nickname_hash = nickname_hash
        user.cbu = body.cbu
        user.cbu_hash = cbu_hash
        user.updated_at = datetime.now()

        await db.commit()
        await db.refresh(user)

        return {"data": user}
