"""Route declaration module for API endpoints configuration."""

from typing import Any

from src.models.models import (
    Questions,
    Profiles,
    Users,
    Institutions,
    UsersInstitutions,
    QuestionAnswers,
    QuestionFeedbacks,
    Subscriptions,
)
from src.schemas import (
    QuestionsBase,
    QuestionsGet,
)
from src.schemas import (
    QuestionAnswersBase,
    QuestionAnswersGet,
    QuestionAnswersPost,
)

from src.schemas import InstitutionBase

from src.configs.db_connection import get_db

routes_declaration: list[dict[str, Any]] = [
    {
        "model_class": Institutions,
        "standard_schema": InstitutionBase,
        "db_session": get_db,
        "auth_callback": None,
        "request_post_schema": None,
        "request_update_schema": None,
        "response_get_schema": None,
        "response_get_by_id_schema": None,
        "response_post_schema": None,
        "response_delete_schema": None,
        "response_patch_schema": None,
        "enable_get": True,
        "enable_get_by_id": True,
        "enable_post": False,
        "enable_delete": False,
        "enable_patch": False,
        "join_parameters": None,
        "second_level_join_parameters": None,
        "route_prefix": "/institutions",
        "route_tags": ["Institutions"],
        "dependencies": False,
    },
    {
        "model_class": QuestionAnswers,
        "standard_schema": QuestionAnswersBase,
        "db_session": get_db,
        "auth_callback": None,
        "request_post_schema": QuestionAnswersPost,
        "request_update_schema": None,
        "response_get_schema": None,
        "response_get_by_id_schema": None,
        "response_post_schema": QuestionAnswersGet,
        "response_delete_schema": None,
        "response_patch_schema": None,
        "enable_get": False,
        "enable_get_by_id": False,
        "enable_post": True,
        "enable_delete": False,
        "enable_patch": False,
        "join_parameters": None,
        "second_level_join_parameters": None,
        "route_prefix": "/question-answers",
        "route_tags": ["Question Answers"],
        "dependencies": True,
    },
]
