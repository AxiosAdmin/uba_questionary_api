from datetime import datetime, timezone
from uuid import uuid4

import jwt

from src.helpers.check_subtopic import check_anatomy_sub_topic
from src.helpers.questions_text import (
    LOCOMOTOR_DESCRIPTIONS,
    NEURO_DESCRIPTIONS,
    SPLACHNOLOGY_DESCRIPTIONS,
)
from src.schemas.users_schemas import UsersGet, UsersPost
from src.utils.constraints import should_bypass_auth
from src.utils.fernet_utils import FernetUtils
from src.utils.jwt_utils import JWTUtils


def test_should_bypass_auth_for_public_routes():
    assert should_bypass_auth("GET", "/healthy") is True
    assert should_bypass_auth("POST", "/stripe/webhook/payment") is True
    assert should_bypass_auth("GET", "/question-answers/latest-answers") is False


def test_should_bypass_auth_for_users_post_only():
    assert should_bypass_auth("POST", "/users") is True
    assert should_bypass_auth("GET", "/users") is False


def test_jwt_utils_round_trip():
    token = JWTUtils.encode_jwt({"id": "user-123", "sub": "user-123"})

    payload = JWTUtils.decode_jwt(token)

    assert payload["id"] == "user-123"
    assert payload["sub"] == "user-123"
    assert payload["exp"] > datetime.now(timezone.utc).timestamp()


def test_jwt_utils_rejects_invalid_token():
    try:
        JWTUtils.decode_jwt("invalid-token")
    except jwt.InvalidTokenError:
        assert True
    else:
        assert False, "Expected an invalid token error"


def test_users_post_encrypts_sensitive_fields():
    body = UsersPost(
        name="Pedro Vieira",
        email="pedro@example.com",
        nickname="pedrov",
        password="secret123",
    )
    fernet = FernetUtils()

    assert body.name != "Pedro Vieira"
    assert body.email != "pedro@example.com"
    assert body.nickname != "pedrov"
    assert body.password != "secret123"
    assert fernet.decrypt(body.name) == "Pedro Vieira"
    assert fernet.decrypt(body.email) == "pedro@example.com"
    assert fernet.decrypt(body.nickname) == "pedrov"
    assert fernet.decrypt(body.password) == "secret123"


def test_users_get_decrypts_sensitive_fields():
    fernet = FernetUtils()

    user = UsersGet(
        id=uuid4(),
        name=fernet.encrypt("Pedro Vieira"),
        email=fernet.encrypt("pedro@example.com"),
        nickname=fernet.encrypt("pedrov"),
        global_role="User",
        created_at=datetime.now(),
        updated_at=None,
    )

    assert user.name == "Pedro Vieira"
    assert user.email == "pedro@example.com"
    assert user.nickname == "pedrov"


def test_users_get_decrypt_fields_returns_original_on_invalid_value():
    assert UsersGet.decrypt_fields("plain-text") == "plain-text"


def test_users_no_password_response_decrypt_fields_returns_original_on_invalid_value():
    from src.schemas.users_schemas import UsersNoPasswordResponse

    assert UsersNoPasswordResponse.decrypt_fields("plain-text") == "plain-text"


def test_users_login_response_decrypt_fields_returns_original_on_invalid_value():
    from src.schemas.users_schemas import UsersLoginResponse

    assert UsersLoginResponse.decrypt_fields("plain-text") == "plain-text"


def test_users_post_encrypt_fields_returns_empty_value():
    assert UsersPost.encrypt_fields("") == ""


def test_check_anatomy_sub_topic_for_locomotor(monkeypatch):
    expected_key = next(iter(LOCOMOTOR_DESCRIPTIONS.keys()))
    monkeypatch.setattr(
        "src.helpers.check_subtopic.random.choice", lambda seq: expected_key
    )

    subtopic, description = check_anatomy_sub_topic("Locomotor")

    assert subtopic == expected_key
    assert description == LOCOMOTOR_DESCRIPTIONS[expected_key]


def test_check_anatomy_sub_topic_for_neuro(monkeypatch):
    expected_key = next(iter(NEURO_DESCRIPTIONS.keys()))
    monkeypatch.setattr(
        "src.helpers.check_subtopic.random.choice", lambda seq: expected_key
    )

    subtopic, description = check_anatomy_sub_topic("Neuroanatomy")

    assert subtopic == expected_key
    assert description == NEURO_DESCRIPTIONS[expected_key]


def test_check_anatomy_sub_topic_for_splanchnology(monkeypatch):
    expected_key = next(iter(SPLACHNOLOGY_DESCRIPTIONS.keys()))
    monkeypatch.setattr(
        "src.helpers.check_subtopic.random.choice", lambda seq: expected_key
    )

    subtopic, description = check_anatomy_sub_topic("Splanchnology")

    assert subtopic == expected_key
    assert description == SPLACHNOLOGY_DESCRIPTIONS[expected_key]


def test_check_anatomy_sub_topic_rejects_unsupported_topic():
    try:
        check_anatomy_sub_topic("Cardiology")
    except ValueError as exc:
        assert "Unsupported anatomy topic" in str(exc)
    else:
        assert False, "Expected unsupported topic error"
