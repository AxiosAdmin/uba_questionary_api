import asyncio
import json
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException

from src.controllers.ai_anatomy_controller import AIAnatomyController
from src.controllers.ai_biology_controller import AIBiologyController
from src.controllers.auth_controller import AuthController
from src.controllers.stripe_controller import StripeController
from src.controllers.users_controller import UsersController
from src.schemas.users_schemas import UsersPost
from src.utils.fernet_utils import FernetUtils
from tests.conftest import FakeAsyncSession, FakeExecuteResult


def test_auth_controller_login_returns_usage_for_institution_user(monkeypatch):
    user_id = uuid4()
    institution_id = uuid4()
    expected_user = SimpleNamespace(
        user=SimpleNamespace(id=user_id),
        institution_id=institution_id,
    )

    async def _login(*args, **kwargs):
        return expected_user

    async def _usage(*args, **kwargs):
        return {"questions_used": 1, "questions_limit": 10, "questions_remaining": 9}

    monkeypatch.setattr("src.controllers.auth_controller.AuthService.login", _login)
    monkeypatch.setattr(
        "src.controllers.auth_controller.SubscriptionService.get_question_generation_usage",
        _usage,
    )
    monkeypatch.setattr(
        "src.controllers.auth_controller.JWTUtils.encode_jwt",
        staticmethod(lambda payload: "jwt-token"),
    )

    response, token = asyncio.run(
        AuthController.login("pedrov", "secret123", FakeAsyncSession())
    )

    assert token == "jwt-token"
    assert response["user"] is expected_user
    assert response["question_generation_usage"]["questions_remaining"] == 9


def test_auth_controller_login_skips_usage_for_admin(monkeypatch):
    admin_id = uuid4()
    expected_user = SimpleNamespace(id=admin_id, global_role="Admin")

    async def _login(*args, **kwargs):
        return expected_user

    monkeypatch.setattr("src.controllers.auth_controller.AuthService.login", _login)
    monkeypatch.setattr(
        "src.controllers.auth_controller.JWTUtils.encode_jwt",
        staticmethod(lambda payload: "jwt-admin"),
    )

    response, token = asyncio.run(
        AuthController.login("admin", "secret123", FakeAsyncSession())
    )

    assert token == "jwt-admin"
    assert response["user"] is expected_user
    assert response["question_generation_usage"] is None


def test_auth_controller_login_translates_value_error_to_http_401(monkeypatch):
    async def _login(*args, **kwargs):
        raise ValueError("Invalid nickname or password")

    monkeypatch.setattr("src.controllers.auth_controller.AuthService.login", _login)

    try:
        asyncio.run(AuthController.login("pedrov", "wrong", FakeAsyncSession()))
    except HTTPException as exc:
        assert exc.status_code == 401
        assert exc.detail == "Invalid nickname or password"
    else:
        assert False, "Expected HTTP 401 for invalid credentials"


def test_auth_controller_login_returns_usage_for_regular_user(monkeypatch):
    expected_user = SimpleNamespace(id=uuid4(), global_role="User")

    async def _login(*args, **kwargs):
        return expected_user

    async def _usage(*args, **kwargs):
        return {
            "questions_used": 4,
            "questions_limit": None,
            "questions_remaining": None,
        }

    monkeypatch.setattr("src.controllers.auth_controller.AuthService.login", _login)
    monkeypatch.setattr(
        "src.controllers.auth_controller.SubscriptionService.get_question_generation_usage",
        _usage,
    )
    monkeypatch.setattr(
        "src.controllers.auth_controller.JWTUtils.encode_jwt",
        staticmethod(lambda payload: "jwt-user"),
    )

    response, token = asyncio.run(
        AuthController.login("user", "secret123", FakeAsyncSession())
    )

    assert token == "jwt-user"
    assert response["user"] is expected_user
    assert response["question_generation_usage"]["questions_used"] == 4


def test_auth_controller_forgot_password_returns_generic_message(monkeypatch):
    async def _request_password_reset(*args, **kwargs):
        return "generated-token"

    sent = {}

    def _send_password_reset_email(recipient, token):
        sent["recipient"] = recipient
        sent["token"] = token

    monkeypatch.setattr(
        "src.controllers.auth_controller.AuthService.request_password_reset",
        _request_password_reset,
    )
    monkeypatch.setattr(
        "src.controllers.auth_controller.EmailService.send_password_reset_email",
        _send_password_reset_email,
    )
    monkeypatch.setattr(
        "src.controllers.auth_controller.settings",
        SimpleNamespace(PASSWORD_RESET_INCLUDE_TOKEN_IN_RESPONSE=False),
    )

    response = asyncio.run(
        AuthController.forgot_password("pedro@example.com", FakeAsyncSession())
    )

    assert response == {
        "message": "If the email exists, password reset instructions have been generated."
    }
    assert sent == {"recipient": "pedro@example.com", "token": "generated-token"}


def test_auth_controller_forgot_password_can_include_token_for_dev(monkeypatch):
    async def _request_password_reset(*args, **kwargs):
        return "generated-token"

    monkeypatch.setattr(
        "src.controllers.auth_controller.AuthService.request_password_reset",
        _request_password_reset,
    )
    monkeypatch.setattr(
        "src.controllers.auth_controller.EmailService.send_password_reset_email",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.controllers.auth_controller.settings",
        SimpleNamespace(PASSWORD_RESET_INCLUDE_TOKEN_IN_RESPONSE=True),
    )

    response = asyncio.run(
        AuthController.forgot_password("pedro@example.com", FakeAsyncSession())
    )

    assert response["reset_token"] == "generated-token"


def test_auth_controller_forgot_password_skips_email_when_user_not_found(monkeypatch):
    async def _request_password_reset(*args, **kwargs):
        return None

    called = {"sent": False}

    def _send_password_reset_email(*args, **kwargs):
        called["sent"] = True

    monkeypatch.setattr(
        "src.controllers.auth_controller.AuthService.request_password_reset",
        _request_password_reset,
    )
    monkeypatch.setattr(
        "src.controllers.auth_controller.EmailService.send_password_reset_email",
        _send_password_reset_email,
    )
    monkeypatch.setattr(
        "src.controllers.auth_controller.settings",
        SimpleNamespace(PASSWORD_RESET_INCLUDE_TOKEN_IN_RESPONSE=False),
    )

    response = asyncio.run(
        AuthController.forgot_password("missing@example.com", FakeAsyncSession())
    )

    assert response == {
        "message": "If the email exists, password reset instructions have been generated."
    }
    assert called["sent"] is False


def test_auth_controller_forgot_password_returns_generic_message_when_email_fails(
    monkeypatch,
):
    async def _request_password_reset(*args, **kwargs):
        return "generated-token"

    def _send_password_reset_email(*args, **kwargs):
        raise RuntimeError("Unable to send password reset email.")

    monkeypatch.setattr(
        "src.controllers.auth_controller.AuthService.request_password_reset",
        _request_password_reset,
    )
    monkeypatch.setattr(
        "src.controllers.auth_controller.EmailService.send_password_reset_email",
        _send_password_reset_email,
    )
    monkeypatch.setattr(
        "src.controllers.auth_controller.settings",
        SimpleNamespace(PASSWORD_RESET_INCLUDE_TOKEN_IN_RESPONSE=False),
    )

    response = asyncio.run(
        AuthController.forgot_password("pedro@example.com", FakeAsyncSession())
    )

    assert response == {
        "message": "If the email exists, password reset instructions have been generated."
    }


def test_auth_controller_reset_password_returns_success(monkeypatch):
    async def _reset_password(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "src.controllers.auth_controller.AuthService.reset_password", _reset_password
    )

    response = asyncio.run(
        AuthController.reset_password("token", "NovaSenha123!", FakeAsyncSession())
    )

    assert response == {"message": "Password updated successfully."}


def test_auth_controller_reset_password_translates_expired_token(monkeypatch):
    async def _reset_password(*args, **kwargs):
        raise jwt.ExpiredSignatureError("expired")

    monkeypatch.setattr(
        "src.controllers.auth_controller.AuthService.reset_password", _reset_password
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            AuthController.reset_password("token", "NovaSenha123!", FakeAsyncSession())
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Password reset token expired"


def test_auth_controller_reset_password_translates_invalid_token(monkeypatch):
    async def _reset_password(*args, **kwargs):
        raise jwt.InvalidTokenError("invalid")

    monkeypatch.setattr(
        "src.controllers.auth_controller.AuthService.reset_password", _reset_password
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            AuthController.reset_password("token", "NovaSenha123!", FakeAsyncSession())
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid password reset token"


def test_auth_controller_reset_password_translates_validation_errors(monkeypatch):
    async def _reset_password(*args, **kwargs):
        raise ValueError("Password must be strong")

    monkeypatch.setattr(
        "src.controllers.auth_controller.AuthService.reset_password", _reset_password
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(AuthController.reset_password("token", "weak", FakeAsyncSession()))

    assert exc.value.status_code == 400
    assert exc.value.detail == "Password must be strong"


def test_users_controller_create_user_rejects_duplicate_nickname(monkeypatch):
    db = FakeAsyncSession()
    body = UsersPost(
        name="Pedro Vieira",
        email="pedro@example.com",
        nickname="pedrov",
        dni="12345678",
        password="Secret123!",
    )

    monkeypatch.setattr(
        UsersController,
        "_find_user_by_email_hash",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=None)),
    )
    monkeypatch.setattr(
        UsersController,
        "_find_user_by_nickname_hash",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=SimpleNamespace(id=uuid4()))),
    )
    monkeypatch.setattr(
        UsersController,
        "_find_user_by_dni_hash",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=None)),
    )
    monkeypatch.setattr(
        UsersController,
        "_find_legacy_duplicate_user",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=None)),
    )

    try:
        asyncio.run(UsersController.create_user(body, db))
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "Nickname, Email or DNI already exists"
    else:
        assert False, "Expected duplicate user error"


def test_users_controller_create_user_persists_unique_user(monkeypatch):
    body = UsersPost(
        name="Pedro Vieira",
        email="pedro@example.com",
        nickname="pedrov",
        dni="12345678",
        password="Secret123!",
    )
    created_user = SimpleNamespace(id=uuid4())
    captured = {}

    async def _create(payload, *args, **kwargs):
        captured["payload"] = payload
        return created_user

    monkeypatch.setattr(
        UsersController.create_user.__globals__["generic_user_service"],
        "create",
        _create,
    )
    monkeypatch.setattr(
        UsersController,
        "_find_user_by_email_hash",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=None)),
    )
    monkeypatch.setattr(
        UsersController,
        "_find_user_by_nickname_hash",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=None)),
    )
    monkeypatch.setattr(
        UsersController,
        "_find_user_by_dni_hash",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=None)),
    )
    monkeypatch.setattr(
        UsersController,
        "_find_legacy_duplicate_user",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=None)),
    )

    response = asyncio.run(UsersController.create_user(body, FakeAsyncSession()))

    assert response == {"data": created_user}
    assert "email_hash" in captured["payload"]
    assert "nickname_hash" in captured["payload"]
    assert "dni_hash" in captured["payload"]


def test_users_controller_create_user_rejects_weak_password():
    body = UsersPost(
        name="Pedro Vieira",
        email="pedro@example.com",
        nickname="pedrov",
        dni="12345678",
        password="secret123",
    )

    try:
        asyncio.run(UsersController.create_user(body, FakeAsyncSession()))
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == (
            "Password must be at least 8 characters long and contain at least "
            "one uppercase letter, one lowercase letter, one number, and one "
            "special character"
        )
    else:
        assert False, "Expected weak password validation error"


def test_users_controller_create_user_rejects_invalid_dni():
    body = UsersPost(
        name="Pedro Vieira",
        email="pedro@example.com",
        nickname="pedrov",
        dni="1234",
        password="Secret123!",
    )

    try:
        asyncio.run(UsersController.create_user(body, FakeAsyncSession()))
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "DNI is invalid"
    else:
        assert False, "Expected invalid DNI validation error"


def test_users_controller_create_user_rejects_duplicate_dni(monkeypatch):
    body = UsersPost(
        name="Pedro Vieira",
        email="pedro@example.com",
        nickname="pedrov",
        dni="12345678",
        password="Secret123!",
    )

    async def _find_by_dni_hash(*args, **kwargs):
        return SimpleNamespace(id=uuid4())

    monkeypatch.setattr(
        UsersController,
        "_find_user_by_email_hash",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=None)),
    )
    monkeypatch.setattr(
        UsersController,
        "_find_user_by_nickname_hash",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=None)),
    )
    monkeypatch.setattr(
        UsersController,
        "_find_user_by_dni_hash",
        staticmethod(_find_by_dni_hash),
    )
    monkeypatch.setattr(
        UsersController,
        "_find_legacy_duplicate_user",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=None)),
    )

    try:
        asyncio.run(UsersController.create_user(body, FakeAsyncSession()))
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "Nickname, Email or DNI already exists"
    else:
        assert False, "Expected duplicate DNI error"


def test_users_controller_create_user_rejects_legacy_duplicate_email(monkeypatch):
    body = UsersPost(
        name="Pedro Vieira",
        email="pedro@example.com",
        nickname="pedrov",
        dni="12345678",
        password="Secret123!",
    )

    monkeypatch.setattr(
        UsersController,
        "_find_user_by_email_hash",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=None)),
    )
    monkeypatch.setattr(
        UsersController,
        "_find_user_by_nickname_hash",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=None)),
    )
    monkeypatch.setattr(
        UsersController,
        "_find_user_by_dni_hash",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=None)),
    )
    monkeypatch.setattr(
        UsersController,
        "_find_legacy_duplicate_user",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=SimpleNamespace(id=uuid4()))),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(UsersController.create_user(body, FakeAsyncSession()))

    assert exc.value.status_code == 400
    assert exc.value.detail == "Nickname, Email or DNI already exists"


def test_users_controller_get_current_user_returns_user(monkeypatch):
    user_id = uuid4()
    expected_user = SimpleNamespace(id=user_id, nickname="pedrov")

    async def _get_user_or_404(request_user_id, db):
        assert request_user_id == user_id
        return expected_user

    monkeypatch.setattr(
        UsersController,
        "_get_user_or_404",
        staticmethod(_get_user_or_404),
    )

    response = asyncio.run(UsersController.get_current_user(user_id, FakeAsyncSession()))

    assert response == {"data": expected_user}


def test_users_controller_find_user_by_hash_helpers_return_matches():
    expected_user = SimpleNamespace(id=uuid4())
    db = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(scalars_items=[expected_user]),
            FakeExecuteResult(scalars_items=[expected_user]),
            FakeExecuteResult(scalars_items=[expected_user]),
        ]
    )

    found_by_dni = asyncio.run(UsersController._find_user_by_dni_hash("hash-1", db))
    found_by_email = asyncio.run(
        UsersController._find_user_by_email_hash("hash-2", db)
    )
    found_by_nickname = asyncio.run(
        UsersController._find_user_by_nickname_hash("hash-3", db)
    )

    assert found_by_dni is expected_user
    assert found_by_email is expected_user
    assert found_by_nickname is expected_user


def test_users_controller_find_legacy_duplicate_user_handles_match_skip_and_miss():
    fernet = FernetUtils()
    matching_email_user = SimpleNamespace(
        id=uuid4(),
        email=fernet.encrypt("pedro@example.com"),
        nickname=fernet.encrypt("other-nickname"),
    )
    matching_nickname_user = SimpleNamespace(
        id=uuid4(),
        email=fernet.encrypt("other@example.com"),
        nickname=fernet.encrypt("pedrov"),
    )
    skipped_user = SimpleNamespace(
        id=uuid4(),
        email=fernet.encrypt("skip@example.com"),
        nickname=fernet.encrypt("pedrov"),
    )
    db_match = FakeAsyncSession(
        execute_results=[FakeExecuteResult(scalars_items=[matching_email_user])]
    )
    db_nickname = FakeAsyncSession(
        execute_results=[FakeExecuteResult(scalars_items=[matching_nickname_user])]
    )
    db_skip = FakeAsyncSession(
        execute_results=[FakeExecuteResult(scalars_items=[skipped_user])]
    )
    db_none = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[])])

    matched = asyncio.run(
        UsersController._find_legacy_duplicate_user(
            "pedro@example.com", "pedrov", db_match
        )
    )
    matched_by_nickname = asyncio.run(
        UsersController._find_legacy_duplicate_user(
            "missing@example.com", "pedrov", db_nickname
        )
    )
    skipped = asyncio.run(
        UsersController._find_legacy_duplicate_user(
            "someone@example.com",
            "pedrov",
            db_skip,
            exclude_user_id=skipped_user.id,
        )
    )
    missing = asyncio.run(
        UsersController._find_legacy_duplicate_user(
            "missing@example.com", "missing", db_none
        )
    )

    assert matched is matching_email_user
    assert matched_by_nickname is matching_nickname_user
    assert skipped is None
    assert missing is None


def test_users_controller_get_user_or_404_raises_when_missing():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(UsersController._get_user_or_404(uuid4(), FakeAsyncSession()))

    assert exc.value.status_code == 404
    assert exc.value.detail == "User not found"


def test_users_controller_get_stored_dni_value_handles_missing_and_plain_values():
    assert UsersController._get_stored_dni_value(SimpleNamespace(dni=None)) == ""
    assert UsersController._get_stored_dni_value(SimpleNamespace(dni="plain-text")) == (
        "plain-text"
    )


def test_users_controller_validate_unique_profile_fields_rejects_duplicates(monkeypatch):
    duplicate_user = SimpleNamespace(id=uuid4())

    monkeypatch.setattr(
        UsersController,
        "_find_user_by_email_hash",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=duplicate_user)),
    )
    monkeypatch.setattr(
        UsersController,
        "_find_user_by_nickname_hash",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=None)),
    )
    monkeypatch.setattr(
        UsersController,
        "_find_user_by_dni_hash",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=None)),
    )
    monkeypatch.setattr(
        UsersController,
        "_find_legacy_duplicate_user",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=None)),
    )

    with pytest.raises(HTTPException) as exc_email:
        asyncio.run(
            UsersController._validate_unique_profile_fields(
                None,
                "pedro@example.com",
                "pedrov",
                "dni-hash",
                FakeAsyncSession(),
            )
        )

    assert exc_email.value.detail == "Nickname, Email or DNI already exists"

    monkeypatch.setattr(
        UsersController,
        "_find_user_by_email_hash",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=None)),
    )
    monkeypatch.setattr(
        UsersController,
        "_find_user_by_nickname_hash",
        staticmethod(lambda *args, **kwargs: asyncio.sleep(0, result=duplicate_user)),
    )

    with pytest.raises(HTTPException) as exc_nickname:
        asyncio.run(
            UsersController._validate_unique_profile_fields(
                None,
                "pedro@example.com",
                "pedrov",
                "dni-hash",
                FakeAsyncSession(),
            )
        )

    assert exc_nickname.value.detail == "Nickname, Email or DNI already exists"


def test_users_controller_update_current_user_updates_hashes_and_fields(monkeypatch):
    user_id = uuid4()
    existing_user = SimpleNamespace(
        id=user_id,
        name="old-name",
        email="old-email",
        email_hash="old-email-hash",
        nickname="old-nickname",
        nickname_hash="old-nickname-hash",
        dni="00000000",
        dni_hash="old-dni-hash",
        updated_at=None,
    )
    body = SimpleNamespace(
        name=FernetUtils().encrypt("Pedro Vieira"),
        email=FernetUtils().encrypt("pedro@example.com"),
        nickname=FernetUtils().encrypt("pedrov"),
        dni=FernetUtils().encrypt("12345678"),
    )
    fake_db = FakeAsyncSession()

    async def _get_user_or_404(request_user_id, db):
        assert request_user_id == user_id
        return existing_user

    async def _validate_unique_profile_fields(
        current_user_id, plain_email, plain_nickname, dni_hash, db
    ):
        assert current_user_id == user_id
        assert plain_email == "pedro@example.com"
        assert plain_nickname == "pedrov"
        assert dni_hash
        return "email-hash", "nickname-hash"

    monkeypatch.setattr(
        UsersController,
        "_get_user_or_404",
        staticmethod(_get_user_or_404),
    )
    monkeypatch.setattr(
        UsersController,
        "_validate_unique_profile_fields",
        staticmethod(_validate_unique_profile_fields),
    )

    response = asyncio.run(
        UsersController.update_current_user(user_id, body, fake_db)
    )

    assert response == {"data": existing_user}
    assert existing_user.name == body.name
    assert existing_user.email == body.email
    assert existing_user.nickname == body.nickname
    assert FernetUtils().decrypt(existing_user.dni) == "12345678"
    assert existing_user.email_hash == "email-hash"
    assert existing_user.nickname_hash == "nickname-hash"
    assert existing_user.dni_hash
    assert existing_user.updated_at is not None
    assert fake_db.committed is True
    assert fake_db.refreshed == [existing_user]


def test_users_controller_update_current_user_rejects_dni_change_for_non_placeholder(
    monkeypatch,
):
    user_id = uuid4()
    existing_user = SimpleNamespace(
        id=user_id,
        dni=FernetUtils().encrypt("12345678"),
    )
    body = SimpleNamespace(
        name=FernetUtils().encrypt("Pedro Vieira"),
        email=FernetUtils().encrypt("pedro@example.com"),
        nickname=FernetUtils().encrypt("pedrov"),
        dni=FernetUtils().encrypt("23456789"),
    )

    async def _get_user_or_404(request_user_id, db):
        assert request_user_id == user_id
        return existing_user

    monkeypatch.setattr(
        UsersController,
        "_get_user_or_404",
        staticmethod(_get_user_or_404),
    )
    monkeypatch.setattr(
        UsersController,
        "_validate_dni",
        staticmethod(lambda encrypted_dni: "23456789"),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            UsersController.update_current_user(user_id, body, FakeAsyncSession())
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "DNI can only be updated for users pending DNI registration"


def test_ai_anatomy_controller_rejects_invalid_institution_id():
    try:
        asyncio.run(
            AIAnatomyController.generate_question(
                "Neuroanatomy",
                FakeAsyncSession(),
                "invalid-uuid",
                str(uuid4()),
            )
        )
    except ValueError as exc:
        assert "Invalid institution_id format" in str(exc)
    else:
        assert False, "Expected invalid institution UUID error"


def test_ai_anatomy_controller_requires_institution_id():
    try:
        asyncio.run(
            AIAnatomyController.generate_question(
                "Neuroanatomy",
                FakeAsyncSession(),
                None,
                str(uuid4()),
            )
        )
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "institution_id is required and must be a valid UUID."
    else:
        assert False, "Expected institution requirement error"


def test_ai_anatomy_controller_requires_authenticated_user():
    try:
        asyncio.run(
            AIAnatomyController.generate_question(
                "Neuroanatomy",
                FakeAsyncSession(),
                str(uuid4()),
                None,
            )
        )
    except HTTPException as exc:
        assert exc.status_code == 401
        assert exc.detail == "Authenticated user is required to generate questions."
    else:
        assert False, "Expected authenticated user requirement"


def test_ai_anatomy_controller_generates_question_and_consumes_quota(monkeypatch):
    institution_id = uuid4()
    user_id = uuid4()
    created_question = SimpleNamespace(id=uuid4(), question="Pergunta final")
    usage = {"questions_used": 2, "questions_limit": 10, "questions_remaining": 8}
    ai_response = SimpleNamespace(
        output=[
            SimpleNamespace(
                content=[
                    SimpleNamespace(
                        text=json.dumps(
                            {
                                "question": "Qual estrutura pertence ao cerebelo?",
                                "answer_a": "Lobo anterior",
                                "answer_b": "Mesencéfalo",
                                "answer_c": "Bulbo",
                                "answer_d": "Tálamo",
                                "explanation_a": "A alternativa A é correta.",
                                "explanation_b": "A alternativa B é incorreta.",
                                "explanation_c": "A alternativa C é incorreta.",
                                "explanation_d": "A alternativa D é incorreta.",
                                "correct_answer": "A",
                            }
                        )
                    )
                ]
            )
        ]
    )
    random_choices = iter(["relationship", "A"])

    async def _validate(*args, **kwargs):
        return None

    async def _last_questions(*args, **kwargs):
        return [SimpleNamespace(question="Pergunta anterior")]

    async def _generate_response(*args, **kwargs):
        return ai_response

    async def _create_question(*args, **kwargs):
        payload = kwargs["question_payload"]
        assert payload["topic"] == "Neuroanatomy"
        assert payload["subtopic"] == "cerebelo"
        assert payload["diversity_mode"] == "relationship"
        assert payload["institution_id"] == institution_id
        return created_question, usage

    monkeypatch.setattr(
        "src.controllers.ai_anatomy_controller.SubscriptionService.validate_question_generation_availability",
        _validate,
    )
    monkeypatch.setattr(
        "src.controllers.ai_anatomy_controller.check_anatomy_sub_topic",
        lambda parameter: ["cerebelo", "estrutura do cerebelo"],
    )
    monkeypatch.setattr(
        "src.controllers.ai_anatomy_controller.random.choice",
        lambda options: next(random_choices),
    )
    monkeypatch.setattr(
        "src.controllers.ai_anatomy_controller.QuestionsService.get_last_three_questions",
        _last_questions,
    )
    monkeypatch.setattr(
        "src.controllers.ai_anatomy_controller.AIAnatomyService.generate_response",
        _generate_response,
    )
    monkeypatch.setattr(
        "src.controllers.ai_anatomy_controller.SubscriptionService.create_question_and_consume_quota",
        _create_question,
    )

    response = asyncio.run(
        AIAnatomyController.generate_question(
            "Neuroanatomy",
            FakeAsyncSession(),
            str(institution_id),
            str(user_id),
        )
    )

    assert response["data"] is created_question
    assert response["question_generation_usage"] == usage


def test_ai_biology_controller_rejects_invalid_institution_id():
    try:
        asyncio.run(
            AIBiologyController.generate_question(
                "Genetica",
                FakeAsyncSession(),
                "invalid-uuid",
                str(uuid4()),
            )
        )
    except ValueError as exc:
        assert "Invalid institution_id format" in str(exc)
    else:
        assert False, "Expected invalid institution UUID error"


def test_ai_biology_controller_requires_institution_id():
    try:
        asyncio.run(
            AIBiologyController.generate_question(
                "Genetica",
                FakeAsyncSession(),
                None,
                str(uuid4()),
            )
        )
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "institution_id is required and must be a valid UUID."
    else:
        assert False, "Expected institution requirement error"


def test_ai_biology_controller_requires_authenticated_user():
    try:
        asyncio.run(
            AIBiologyController.generate_question(
                "Genetica",
                FakeAsyncSession(),
                str(uuid4()),
                None,
            )
        )
    except HTTPException as exc:
        assert exc.status_code == 401
        assert exc.detail == "Authenticated user is required to generate questions."
    else:
        assert False, "Expected authenticated user requirement"


def test_ai_biology_controller_generates_question_and_consumes_quota(monkeypatch):
    institution_id = uuid4()
    user_id = uuid4()
    created_question = SimpleNamespace(id=uuid4(), question="Pergunta final")
    usage = {"questions_used": 2, "questions_limit": 10, "questions_remaining": 8}
    ai_response = SimpleNamespace(
        output=[
            SimpleNamespace(
                content=[
                    SimpleNamespace(
                        text=json.dumps(
                            {
                                "question": "Qual alteracao caracteriza a heranca mitocondrial?",
                                "answer_a": "Transmissao exclusivamente materna",
                                "answer_b": "Transmissao exclusivamente paterna",
                                "answer_c": "Segregacao mendeliana classica",
                                "answer_d": "Ausencia de heteroplasmia",
                                "explanation_a": "A alternativa A e correta.",
                                "explanation_b": "A alternativa B e incorreta.",
                                "explanation_c": "A alternativa C e incorreta.",
                                "explanation_d": "A alternativa D e incorreta.",
                                "correct_answer": "A",
                            }
                        )
                    )
                ]
            )
        ]
    )
    random_choices = iter(["mechanism", "A"])

    async def _validate(*args, **kwargs):
        return None

    async def _last_questions(*args, **kwargs):
        return [SimpleNamespace(question="Pergunta anterior")]

    async def _generate_response(*args, **kwargs):
        return ai_response

    async def _create_question(*args, **kwargs):
        payload = kwargs["question_payload"]
        assert payload["topic"] == "Genetica"
        assert payload["subtopic"] == "herencia_mitocondrial"
        assert payload["diversity_mode"] == "mechanism"
        assert payload["institution_id"] == institution_id
        return created_question, usage

    monkeypatch.setattr(
        "src.controllers.ai_biology_controller.SubscriptionService.validate_question_generation_availability",
        _validate,
    )
    monkeypatch.setattr(
        "src.controllers.ai_biology_controller.check_biology_sub_topic",
        lambda parameter: ["herencia_mitocondrial", "transmision y heteroplasmia"],
    )
    monkeypatch.setattr(
        "src.controllers.ai_biology_controller.random.choice",
        lambda options: next(random_choices),
    )
    monkeypatch.setattr(
        "src.controllers.ai_biology_controller.QuestionsService.get_last_three_questions",
        _last_questions,
    )
    monkeypatch.setattr(
        "src.controllers.ai_biology_controller.AIBiologyService.generate_response",
        _generate_response,
    )
    monkeypatch.setattr(
        "src.controllers.ai_biology_controller.SubscriptionService.create_question_and_consume_quota",
        _create_question,
    )

    response = asyncio.run(
        AIBiologyController.generate_question(
            "Genetica",
            FakeAsyncSession(),
            str(institution_id),
            str(user_id),
        )
    )

    assert response["data"] is created_question
    assert response["question_generation_usage"] == usage


def test_stripe_controller_generate_payment_checkout_returns_url(monkeypatch):
    monkeypatch.setattr(
        "src.controllers.stripe_controller.UserService.get_user_checkout_contact",
        lambda *args, **kwargs: asyncio.sleep(
            0,
            result={
                "id": uuid4(),
                "email": "pedro@example.com",
                "has_pending_dni": False,
            },
        ),
    )
    captured = {}

    def _generate_checkout(user_id, customer_email=None, coupon_code=None):
        captured["user_id"] = user_id
        captured["customer_email"] = customer_email
        captured["coupon_code"] = coupon_code
        return {"url_session": "https://checkout.stripe.test"}

    monkeypatch.setattr(
        "src.controllers.stripe_controller.StripeService.generate_payment_checkout",
        staticmethod(_generate_checkout),
    )

    response = asyncio.run(
        StripeController.generate_payment_checkout(
            str(uuid4()), FakeAsyncSession(), "PROMO-UBA"
        )
    )

    assert response == {"url_session": "https://checkout.stripe.test"}
    assert captured["customer_email"] == "pedro@example.com"
    assert captured["coupon_code"] == "PROMO-UBA"


def test_stripe_controller_generate_payment_checkout_returns_404_when_user_missing(
    monkeypatch,
):
    monkeypatch.setattr(
        "src.controllers.stripe_controller.UserService.get_user_checkout_contact",
        lambda *args, **kwargs: asyncio.sleep(0, result=None),
    )

    response = asyncio.run(
        StripeController.generate_payment_checkout(str(uuid4()), FakeAsyncSession())
    )

    assert response.status_code == 404
    assert response.body == b'{"message":"User doesn\'t exists"}'


def test_stripe_controller_generate_payment_checkout_rejects_pending_dni(
    monkeypatch,
):
    monkeypatch.setattr(
        "src.controllers.stripe_controller.UserService.get_user_checkout_contact",
        lambda *args, **kwargs: asyncio.sleep(
            0,
            result={
                "id": uuid4(),
                "email": "pedro@example.com",
                "has_pending_dni": True,
            },
        ),
    )

    response = asyncio.run(
        StripeController.generate_payment_checkout(str(uuid4()), FakeAsyncSession())
    )

    assert response.status_code == 400
    assert (
        response.body
        == b'{"detail":"You must update your DNI before starting the checkout"}'
    )


def test_stripe_controller_generate_payment_checkout_returns_400_for_invalid_coupon(
    monkeypatch,
):
    monkeypatch.setattr(
        "src.controllers.stripe_controller.UserService.get_user_checkout_contact",
        lambda *args, **kwargs: asyncio.sleep(
            0,
            result={
                "id": uuid4(),
                "email": "pedro@example.com",
                "has_pending_dni": False,
            },
        ),
    )

    def _generate_checkout(*args, **kwargs):
        raise ValueError("Coupon code is invalid or inactive")

    monkeypatch.setattr(
        "src.controllers.stripe_controller.StripeService.generate_payment_checkout",
        staticmethod(_generate_checkout),
    )

    response = asyncio.run(
        StripeController.generate_payment_checkout(
            str(uuid4()), FakeAsyncSession(), "PROMO-UBA"
        )
    )

    assert response.status_code == 400
    assert response.body == b'{"message":"Coupon code is invalid or inactive"}'


def test_stripe_controller_webhook_dispatches_to_expected_service(monkeypatch):
    async def _async_payment_succeeded(payload, db):
        return {"status": "processed", "event": payload["type"]}

    monkeypatch.setattr(
        "src.controllers.stripe_controller.StripeService.checkout_session_async_payment_succeeded",
        _async_payment_succeeded,
    )

    response = asyncio.run(
        StripeController.payment_response_webhook(
            {
                "type": "checkout.session.async_payment_succeeded",
                "data": {"object": {}},
            },
            FakeAsyncSession(),
        )
    )

    assert response == {
        "status": "processed",
        "event": "checkout.session.async_payment_succeeded",
    }


@pytest.mark.parametrize(
    ("event_type", "service_name"),
    [
        ("checkout.session.completed", "checkout_session_completed"),
        (
            "checkout.session.async_payment_succeeded",
            "checkout_session_async_payment_succeeded",
        ),
        (
            "checkout.session.async_payment_failed",
            "checkout_session_async_payment_failed",
        ),
        ("charge.succeeded", "charge_succeeded"),
        ("charge.failed", "charge_failed"),
        ("charge.updated", "charge_updated"),
        ("charge.dispute.created", "charge_dispute_created"),
        ("charge.dispute.closed", "charge_dispute_closed"),
        (
            "radar.early_fraud_warning.created",
            "radar_early_fraud_warning_created",
        ),
    ],
)
def test_stripe_controller_webhook_dispatches_all_supported_events(
    monkeypatch, event_type, service_name
):
    async def _handler(payload, db):
        return {"event": payload["type"]}

    monkeypatch.setattr(
        f"src.controllers.stripe_controller.StripeService.{service_name}",
        _handler,
    )

    response = asyncio.run(
        StripeController.payment_response_webhook(
            {"type": event_type, "data": {"object": {}}},
            FakeAsyncSession(),
        )
    )

    assert response == {"event": event_type}


def test_stripe_controller_webhook_ignores_unknown_event():
    response = asyncio.run(
        StripeController.payment_response_webhook(
            {"type": "unknown.event", "data": {"object": {}}},
            FakeAsyncSession(),
        )
    )

    assert response == {"status": "ignored"}


def test_stripe_controller_webhook_normalizes_nested_stripe_objects(monkeypatch):
    class _StripeLikeObject:
        def __init__(self, payload):
            self._payload = payload

        def _to_dict_recursive(self):
            return self._payload

    async def _completed(payload, db):
        assert payload == {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_123",
                    "payment_status": "paid",
                    "customer": "cus_123",
                }
            },
        }
        return {"status": "processed"}

    monkeypatch.setattr(
        "src.controllers.stripe_controller.StripeService.checkout_session_completed",
        _completed,
    )

    response = asyncio.run(
        StripeController.payment_response_webhook(
            _StripeLikeObject(
                {
                    "type": "checkout.session.completed",
                    "data": {
                        "object": _StripeLikeObject(
                            {
                                "id": "cs_123",
                                "payment_status": "paid",
                                "customer": "cus_123",
                            }
                        )
                    },
                }
            ),
            FakeAsyncSession(),
        )
    )

    assert response == {"status": "processed"}
