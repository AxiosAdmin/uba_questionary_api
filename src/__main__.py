"""Main API File"""

from fastapi import FastAPI, Depends
from fastapi.security import APIKeyHeader, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from api_crud_generate_libary.routers.router import Router

from src.routers import (
    ai_anatomy_router,
    auth_router,
    users_router,
    question_answers_router,
    stripe_router
)
from src.configs.configs import settings
from src.models import routes_declaration
from src.middleware.jwt_middleware import jwt_checker

security = HTTPBearer(auto_error=False)
institution_id = APIKeyHeader(name="x-institution-id", auto_error=False)

app = FastAPI()

app.middleware("http")(jwt_checker)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthy")
def healthy():
    """Healthy check route"""
    return {"status": "Ok"}


app.include_router(
    auth_router,
    prefix="",
    tags=["Authentication"],
)

app.include_router(
    users_router,
    prefix="/users",
    tags=["Users"],
)

app.include_router(
    question_answers_router,
    prefix="/question-answers",
    tags=["Question Answers"],
    dependencies=[Depends(institution_id), Depends(security)],
)

for route in routes_declaration:
    item = Router(
        model_class=route["model_class"],
        standard_schema=route["standard_schema"],
        db_session=route["db_session"],
        request_post_schema=route["request_post_schema"],
        request_patch_schema=route["request_update_schema"],
        response_get_schema=route["response_get_schema"],
        response_get_by_id_schema=route["response_get_by_id_schema"],
        response_post_schema=route["response_post_schema"],
        response_delete_schema=route["response_delete_schema"],
        response_patch_schema=route["response_patch_schema"],
        use_get=route["enable_get"],
        use_get_by_id=route["enable_get_by_id"],
        use_post=route["enable_post"],
        use_delete=route["enable_delete"],
        use_patch=route["enable_patch"],
        auth_callback=[institution_id, security] if route["dependencies"] else None,
        join_parameters=route["join_parameters"],
        second_level_join_parameters=route["second_level_join_parameters"],
    )

    app.include_router(
        item.router, prefix=route["route_prefix"], tags=route["route_tags"]
    )

app.include_router(
    stripe_router,
    prefix="/stripe",
    tags=["Stripe"],
)

app.include_router(
    ai_anatomy_router,
    prefix="/ai",
    tags=["Anatomy"],
    dependencies=[Depends(institution_id), Depends(security)],
)
