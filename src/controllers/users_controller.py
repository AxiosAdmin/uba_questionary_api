"""Controller for Users table"""

from datetime import datetime
import logging
import re
from uuid import uuid4

from fastapi import HTTPException
from api_crud_generate_libary.services.service import Service
from sqlalchemy import or_, select
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError

from src.models import Users
from src.services.stripe_service import StripeService
from src.utils.dni_utils import DniUtils
from src.utils.fernet_utils import FernetUtils
from src.utils.password_utils import (
    PASSWORD_REQUIREMENTS_MESSAGE,
    validate_password_requirements,
)
from src.utils.user_lookup_utils import UserLookupUtils

fernet = FernetUtils()
generic_user_service = Service(Users)
logger = logging.getLogger(__name__)
DUPLICATE_USER_DETAIL = "Nickname, Email or DNI already exists"
DNI_UPDATE_FORBIDDEN_DETAIL = (
    "DNI can only be updated for users pending DNI registration"
)
MISSING_DNI_PLACEHOLDER = "00000000"
STRIPE_CUSTOMER_CREATION_UNAVAILABLE_DETAIL = (
    "Stripe customer creation is unavailable. Try again later."
)
OUTDATED_DATABASE_SCHEMA_DETAIL = (
    "Database schema is outdated. Run the pending migrations and try again."
)
DATABASE_OPERATION_UNAVAILABLE_DETAIL = (
    "User persistence is temporarily unavailable. Try again later."
)
MISSING_COLUMN_MIGRATIONS = {
    "users.email_hash": "src/databases/scripts/migrations/users_cbu.sql",
    "users.nickname_hash": "src/databases/scripts/migrations/users_cbu.sql",
    "users.dni": "src/databases/scripts/migrations/users_dni.sql",
    "users.dni_hash": "src/databases/scripts/migrations/users_dni.sql",
    "users.stripe_customer_id": (
        "src/databases/scripts/migrations/users_stripe_customer_id.sql"
    ),
}


class UsersController:
    """Controller class for handling user-related operations."""

    @staticmethod
    def _get_programming_error_detail(exc: Exception) -> str:
        """Return a more actionable detail for known schema mismatches."""
        error_message = str(exc)
        column_match = re.search(r"column\s+([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)\s+does not exist", error_message)
        if not column_match:
            return OUTDATED_DATABASE_SCHEMA_DETAIL

        missing_column = column_match.group(1)
        migration_path = MISSING_COLUMN_MIGRATIONS.get(missing_column)

        if migration_path:
            return (
                f"Database schema mismatch: missing column {missing_column}. "
                f"Run the migration `{migration_path}` and try again."
            )

        return (
            f"Database schema mismatch: missing column {missing_column}. "
            "Run the pending migrations and try again."
        )

    @staticmethod
    async def _raise_handled_database_error(db, action: str, exc: Exception):
        """Rollback and translate persistence errors to handled HTTP responses."""
        try:
            await db.rollback()
        except Exception:  # pylint: disable=broad-exception-caught
            pass

        if isinstance(exc, ProgrammingError):
            logger.warning("UsersController %s failed: %s", action, exc)
            raise HTTPException(
                status_code=503,
                detail=UsersController._get_programming_error_detail(exc),
            ) from None

        logger.warning("UsersController %s failed: %s", action, exc)
        raise HTTPException(
            status_code=503,
            detail=DATABASE_OPERATION_UNAVAILABLE_DETAIL,
        ) from None

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
    def _validate_dni(encrypted_dni: str) -> str:
        try:
            return DniUtils.normalize_and_validate(fernet.decrypt(encrypted_dni))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="DNI is invalid") from exc

    @staticmethod
    async def _find_user_by_dni_hash(dni_hash: str, db):
        result = await db.execute(select(Users).where(Users.dni_hash == dni_hash))
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
    def _get_stored_dni_value(user) -> str:
        raw_dni = getattr(user, "dni", None)
        if not raw_dni:
            return ""

        try:
            return fernet.decrypt(raw_dni)
        except Exception:  # pylint: disable=broad-exception-caught
            return raw_dni

    @staticmethod
    async def _validate_unique_profile_fields(
        current_user_id, plain_email, plain_nickname, dni_hash, db
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

        existing_dni_user = await UsersController._find_user_by_dni_hash(dni_hash, db)
        if existing_dni_user is not None and existing_dni_user.id != current_user_id:
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
        try:
            UsersController._validate_password_requirements(body.password)
            normalized_dni = UsersController._validate_dni(body.dni)
            dni_hash = DniUtils.hash_normalized(normalized_dni)
            plain_email = fernet.decrypt(body.email)
            plain_nickname = fernet.decrypt(body.nickname)
            email_hash, nickname_hash = (
                await UsersController._validate_unique_profile_fields(
                    None,
                    plain_email,
                    plain_nickname,
                    dni_hash,
                    db,
                )
            )
            plain_name = fernet.decrypt(body.name)
            new_user_id = uuid4()

            try:
                stripe_customer_id = StripeService.create_customer(
                    user_id=new_user_id,
                    customer_email=plain_email,
                    customer_name=plain_name,
                )
            except ValueError as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            except Exception as exc:  # pylint: disable=broad-exception-caught
                raise HTTPException(
                    status_code=503,
                    detail=STRIPE_CUSTOMER_CREATION_UNAVAILABLE_DETAIL,
                ) from exc

            new_user_payload = body.model_dump()
            new_user_payload["id"] = new_user_id
            new_user_payload["dni"] = fernet.encrypt(normalized_dni)
            new_user_payload["email_hash"] = email_hash
            new_user_payload["nickname_hash"] = nickname_hash
            new_user_payload["dni_hash"] = dni_hash
            new_user_payload["stripe_customer_id"] = stripe_customer_id
            new_user = await generic_user_service.create(
                new_user_payload,
                db,
                join_parameters=None,
                second_level_join_parameters=None,
            )
        except ValueError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except SQLAlchemyError as exc:
            await UsersController._raise_handled_database_error(db, "create_user", exc)

        return {"data": new_user}

    @staticmethod
    async def get_current_user(user_id, db):
        """Return the authenticated user profile."""
        user = await UsersController._get_user_or_404(user_id, db)
        return {"data": user}

    @staticmethod
    async def update_current_user(user_id, body, db):
        """Update the authenticated user's public profile fields."""
        try:
            user = await UsersController._get_user_or_404(user_id, db)
            current_dni = UsersController._get_stored_dni_value(user)
            normalized_dni = UsersController._validate_dni(body.dni)
            if current_dni != MISSING_DNI_PLACEHOLDER:
                current_normalized_dni = DniUtils.normalize(current_dni)
                if normalized_dni != current_normalized_dni:
                    raise HTTPException(
                        status_code=400,
                        detail=DNI_UPDATE_FORBIDDEN_DETAIL,
                    )

            dni_hash = DniUtils.hash_normalized(normalized_dni)
            plain_email = fernet.decrypt(body.email)
            plain_nickname = fernet.decrypt(body.nickname)
            email_hash, nickname_hash = (
                await UsersController._validate_unique_profile_fields(
                    user.id,
                    plain_email,
                    plain_nickname,
                    dni_hash,
                    db,
                )
            )

            user.name = body.name
            user.email = body.email
            user.email_hash = email_hash
            user.nickname = body.nickname
            user.nickname_hash = nickname_hash
            user.dni = fernet.encrypt(normalized_dni)
            user.dni_hash = dni_hash
            user.updated_at = datetime.now()

            await db.commit()
            await db.refresh(user)
        except SQLAlchemyError as exc:
            await UsersController._raise_handled_database_error(
                db, "update_current_user", exc
            )

        return {"data": user}
