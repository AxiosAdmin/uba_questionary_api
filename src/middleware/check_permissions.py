from fastapi import HTTPException
from api_crud_generate_libary.services.service import Service

from src.models import Users
from src.services.auth_service import AuthService
from src.services.user_institution_service import UserInstitutionService
from src.helpers.permissions_list import PERMISSIONS

users_service = Service(Users)


def _permission_error_detail(error: Exception) -> str | dict | list:
    detail = getattr(error, "detail", None)
    if detail:
        return detail

    detail = getattr(error, "__dict__", {}).get("detail")
    if detail:
        return detail

    return "User does not have permission to access the institution"


async def check_permissions(institution_id, user_id, method, url_path, db):
    """
    Middleware to check user permissions for protected routes.

    Args:
        session: The database session
        user_role: The role of the authenticated user
        institution_id: The ID of the institution to which the user belongs
        user_id: The ID of the authenticated user
        url_path: The path of the requested URL

    Returns:
        bool: True if the user has permission to access the route, False otherwise
    """

    user = await users_service.read_one(
        user_id,
        db,
        join_parameters=None,
        second_level_join_parameters=None,
    )

    if user.global_role == "Admin":
        return True

    if not await AuthService.user_has_active_subscription(user.id, db):
        raise HTTPException(status_code=403, detail="Active subscription required")

    user_institution = await UserInstitutionService.read_user_institutions(
        str(user_id), str(institution_id), db
    )

    if not user_institution:
        raise HTTPException(
            status_code=403, detail="User does not belong to the institution"
        )

    try:
        profile_permissions = PERMISSIONS.get(user_institution.profile.name)
        if not profile_permissions:
            raise HTTPException(
                status_code=403,
                detail="User does not have permission to access the institution",
            )

        context = url_path.strip("/").split("/")[0]
        allowed_methods = profile_permissions.get(context)

        if not allowed_methods or method not in allowed_methods:
            raise HTTPException(
                status_code=403,
                detail="This profile do not have access to this content",
            )

        return True
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=403,
            detail=_permission_error_detail(e),
        ) from e
