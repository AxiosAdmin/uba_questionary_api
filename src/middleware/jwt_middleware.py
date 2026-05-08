import jwt

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

from src.utils.jwt_utils import JWTUtils
from src.utils.constraints import should_bypass_auth
from src.configs.db_connection import async_session
from src.middleware.check_permissions import check_permissions


async def jwt_checker(request: Request, call_next):
    """
    Middleware to validate JWT tokens for protected routes.

    Args:
        request: The incoming HTTP request
        call_next: The next middleware or route handler in the chain

    Returns:
        Response: Either an error response if token is invalid, or the next handler's response
    """
    bypass_auth = request.method == "OPTIONS" or should_bypass_auth(
        request.method, request.url.path
    )

    if bypass_auth:
        return await call_next(request)

    authorization = request.headers.get("authorization")
    if not authorization:
        return JSONResponse(
            status_code=401, content={"detail": "Authorization header is required"}
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid authorization format. Use: Bearer <token>"},
        )

    try:
        decoded_token = JWTUtils.decode_jwt(token)
        async with async_session() as session:
            await check_permissions(
                request.headers.get("x-institution-id"),
                decoded_token["id"],
                request.method,
                request.url.path,
                session,
            )
        request.state.user_id = decoded_token["id"]

    except jwt.ExpiredSignatureError:
        return JSONResponse(status_code=401, content={"detail": "Token expired"})
    except (jwt.InvalidTokenError, HTTPException) as e:
        status_code = getattr(e, "status_code", 401)
        detail = getattr(e, "detail", "Invalid token")
        return JSONResponse(status_code=status_code, content={"detail": detail})

    return await call_next(request)
