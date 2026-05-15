import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.configs.configs import Settings
from src.configs import db_connection
from src.controllers.question_answers_controller import QuestionAnswersController
from src.middleware.check_permissions import check_permissions, _permission_error_detail
from src.services.institutions_service import InstitutionsService
from src.services.user_institution_service import UserInstitutionService
from src.utils.fernet_utils import FernetUtils
from tests.conftest import FakeAsyncSession, FakeExecuteResult


def test_settings_parse_frontend_origins_from_json():
    value = Settings.parse_frontend_origins('["http://localhost:3000", "https://example.com"]')

    assert value == ["http://localhost:3000", "https://example.com"]


def test_settings_parse_frontend_origins_from_csv():
    value = Settings.parse_frontend_origins("http://localhost:3000, https://example.com")

    assert value == ["http://localhost:3000", "https://example.com"]


def test_settings_parse_frontend_origins_from_list():
    value = Settings.parse_frontend_origins(["http://localhost:3000"])

    assert value == ["http://localhost:3000"]


def test_settings_builds_database_url():
    settings = Settings()

    assert settings.database_url == (
        "postgresql+asyncpg://"
        "test_user:test_password@localhost:5432/test_db"
    )


def test_get_db_yields_and_closes_session(monkeypatch):
    fake_session = FakeAsyncSession()
    monkeypatch.setattr(db_connection, "async_session", lambda: fake_session)

    async def _run():
        generator = db_connection.get_db()
        session = await anext(generator)
        assert session is fake_session
        with pytest.raises(StopAsyncIteration):
            await anext(generator)

    asyncio.run(_run())

    assert fake_session.closed is True
    assert fake_session.rolled_back is False


def test_get_db_rolls_back_and_closes_session_on_error(monkeypatch):
    fake_session = FakeAsyncSession()
    monkeypatch.setattr(db_connection, "async_session", lambda: fake_session)

    async def _run():
        generator = db_connection.get_db()
        await anext(generator)
        with pytest.raises(RuntimeError, match="boom"):
            await generator.athrow(RuntimeError("boom"))

    asyncio.run(_run())

    assert fake_session.rolled_back is True
    assert fake_session.closed is True


def test_question_answers_controller_delegates_to_service(monkeypatch):
    expected = {"data": [{"id": str(uuid4())}]}

    async def _service(user_id, db):
        return expected

    monkeypatch.setattr(
        "src.controllers.question_answers_controller.QuestionAnswersService.get_questions_with_latest_user_answers",
        _service,
    )

    response = asyncio.run(
        QuestionAnswersController.get_questions_with_latest_user_answers(
            uuid4(), FakeAsyncSession()
        )
    )

    assert response is expected


def test_permission_error_detail_returns_exception_detail_attribute():
    error = HTTPException(status_code=403, detail="custom detail")

    response = _permission_error_detail(error)

    assert response == "custom detail"


def test_permission_error_detail_returns_detail_from_exception_dict():
    class CustomError(Exception):
        def __init__(self, detail):
            super().__init__("boom")
            self.detail = detail

    response = _permission_error_detail(CustomError({"message": "custom detail"}))

    assert response == {"message": "custom detail"}


def test_permission_error_detail_returns_default_message_without_detail():
    response = _permission_error_detail(RuntimeError("boom"))

    assert response == "User does not have permission to access the institution"


def test_check_permissions_allows_admin(monkeypatch):
    async def _read_one(*args, **kwargs):
        return SimpleNamespace(id=uuid4(), global_role="Admin")

    monkeypatch.setattr(
        check_permissions.__globals__["users_service"], "read_one", _read_one
    )

    response = asyncio.run(
        check_permissions(str(uuid4()), str(uuid4()), "GET", "/institutions", FakeAsyncSession())
    )

    assert response is True


def test_check_permissions_requires_active_subscription(monkeypatch):
    user = SimpleNamespace(id=uuid4(), global_role="User")

    async def _read_one(*args, **kwargs):
        return user

    async def _subscription(*args, **kwargs):
        return False

    monkeypatch.setattr(
        check_permissions.__globals__["users_service"], "read_one", _read_one
    )
    monkeypatch.setattr(
        "src.middleware.check_permissions.AuthService.user_has_active_subscription",
        _subscription,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            check_permissions(str(uuid4()), str(uuid4()), "GET", "/institutions", FakeAsyncSession())
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Active question package required"


def test_check_permissions_allows_latest_answers_without_active_subscription(monkeypatch):
    user = SimpleNamespace(id=uuid4(), global_role="User")
    membership = SimpleNamespace(profile=SimpleNamespace(name="basic_uba_user"))

    async def _read_one(*args, **kwargs):
        return user

    async def _subscription(*args, **kwargs):
        return False

    async def _read_user_institutions(*args, **kwargs):
        return membership

    monkeypatch.setattr(
        check_permissions.__globals__["users_service"], "read_one", _read_one
    )
    monkeypatch.setattr(
        "src.middleware.check_permissions.AuthService.user_has_active_subscription",
        _subscription,
    )
    monkeypatch.setattr(
        "src.middleware.check_permissions.UserInstitutionService.read_user_institutions",
        _read_user_institutions,
    )

    response = asyncio.run(
        check_permissions(
            str(uuid4()),
            str(uuid4()),
            "GET",
            "/question-answers/latest-answers",
            FakeAsyncSession(),
        )
    )

    assert response is True


def test_check_permissions_requires_user_membership(monkeypatch):
    user = SimpleNamespace(id=uuid4(), global_role="User")

    async def _read_one(*args, **kwargs):
        return user

    async def _subscription(*args, **kwargs):
        return True

    async def _read_user_institutions(*args, **kwargs):
        return None

    monkeypatch.setattr(
        check_permissions.__globals__["users_service"], "read_one", _read_one
    )
    monkeypatch.setattr(
        "src.middleware.check_permissions.AuthService.user_has_active_subscription",
        _subscription,
    )
    monkeypatch.setattr(
        "src.middleware.check_permissions.UserInstitutionService.read_user_institutions",
        _read_user_institutions,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            check_permissions(str(uuid4()), str(uuid4()), "GET", "/institutions", FakeAsyncSession())
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "User does not belong to the institution"


def test_check_permissions_requires_profile_permissions(monkeypatch):
    user = SimpleNamespace(id=uuid4(), global_role="User")
    membership = SimpleNamespace(profile=SimpleNamespace(name="unknown_profile"))

    async def _read_one(*args, **kwargs):
        return user

    async def _subscription(*args, **kwargs):
        return True

    async def _read_user_institutions(*args, **kwargs):
        return membership

    monkeypatch.setattr(
        check_permissions.__globals__["users_service"], "read_one", _read_one
    )
    monkeypatch.setattr(
        "src.middleware.check_permissions.AuthService.user_has_active_subscription",
        _subscription,
    )
    monkeypatch.setattr(
        "src.middleware.check_permissions.UserInstitutionService.read_user_institutions",
        _read_user_institutions,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            check_permissions(str(uuid4()), str(uuid4()), "GET", "/question-answers", FakeAsyncSession())
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "User does not have permission to access the institution"


def test_check_permissions_allows_profile_action(monkeypatch):
    user = SimpleNamespace(id=uuid4(), global_role="User")
    membership = SimpleNamespace(profile=SimpleNamespace(name="basic_uba_user"))

    async def _read_one(*args, **kwargs):
        return user

    async def _subscription(*args, **kwargs):
        return True

    async def _read_user_institutions(*args, **kwargs):
        return membership

    monkeypatch.setattr(
        check_permissions.__globals__["users_service"], "read_one", _read_one
    )
    monkeypatch.setattr(
        "src.middleware.check_permissions.AuthService.user_has_active_subscription",
        _subscription,
    )
    monkeypatch.setattr(
        "src.middleware.check_permissions.UserInstitutionService.read_user_institutions",
        _read_user_institutions,
    )

    response = asyncio.run(
        check_permissions(str(uuid4()), str(uuid4()), "POST", "/ai/anatomy", FakeAsyncSession())
    )

    assert response is True


def test_check_permissions_denies_invalid_context(monkeypatch):
    user = SimpleNamespace(id=uuid4(), global_role="User")
    membership = SimpleNamespace(profile=SimpleNamespace(name="basic_uba_user"))

    async def _read_one(*args, **kwargs):
        return user

    async def _subscription(*args, **kwargs):
        return True

    async def _read_user_institutions(*args, **kwargs):
        return membership

    monkeypatch.setattr(
        check_permissions.__globals__["users_service"], "read_one", _read_one
    )
    monkeypatch.setattr(
        "src.middleware.check_permissions.AuthService.user_has_active_subscription",
        _subscription,
    )
    monkeypatch.setattr(
        "src.middleware.check_permissions.UserInstitutionService.read_user_institutions",
        _read_user_institutions,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            check_permissions(str(uuid4()), str(uuid4()), "GET", "/institutions", FakeAsyncSession())
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "This profile do not have access to this content"


def test_check_permissions_wraps_unexpected_permission_errors(monkeypatch):
    user = SimpleNamespace(id=uuid4(), global_role="User")
    membership = SimpleNamespace(profile=SimpleNamespace(name="basic_uba_user"))

    async def _read_one(*args, **kwargs):
        return user

    async def _subscription(*args, **kwargs):
        return True

    async def _read_user_institutions(*args, **kwargs):
        return membership

    class BrokenPermissions(dict):
        def get(self, key, default=None):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        check_permissions.__globals__["users_service"], "read_one", _read_one
    )
    monkeypatch.setattr(
        "src.middleware.check_permissions.AuthService.user_has_active_subscription",
        _subscription,
    )
    monkeypatch.setattr(
        "src.middleware.check_permissions.UserInstitutionService.read_user_institutions",
        _read_user_institutions,
    )
    monkeypatch.setattr(
        "src.middleware.check_permissions.PERMISSIONS",
        BrokenPermissions(),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            check_permissions(str(uuid4()), str(uuid4()), "GET", "/question-answers", FakeAsyncSession())
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "User does not have permission to access the institution"


def test_institutions_service_returns_uba_institution():
    expected = SimpleNamespace(id=uuid4(), name="UBA")
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[expected])])

    response = asyncio.run(InstitutionsService.get_uba_institution(db))

    assert response is expected


def test_user_institution_service_rejects_invalid_uuid():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            UserInstitutionService.read_user_institutions(
                "invalid",
                str(uuid4()),
                FakeAsyncSession(),
            )
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Incorrect Id format"


def test_user_institution_service_returns_membership():
    expected = SimpleNamespace(id=uuid4())
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[expected])])

    response = asyncio.run(
        UserInstitutionService.read_user_institutions(str(uuid4()), str(uuid4()), db)
    )

    assert response is expected


def test_fernet_utils_accepts_custom_key():
    custom_key = b"V9M6GgD4xih0qvA4RqgQhQYv7xYIB3IYk6Y0dA6g0tI="
    fernet = FernetUtils(key=custom_key)

    encrypted = fernet.encrypt("hello")

    assert fernet.decrypt(encrypted) == "hello"
