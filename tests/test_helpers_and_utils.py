from datetime import datetime, timezone
from uuid import uuid4

import jwt

from src.helpers.biologia_questionary_text import (
    BIOLOGIA_CELULAR_Y_MOLECULAR_DESCRIPTIONS,
    GENETICA_DESCRIPTIONS,
)
from src.helpers.check_subtopic import check_anatomy_sub_topic, check_biology_sub_topic
from src.helpers.questions_text import (
    LOCOMOTOR_DESCRIPTIONS,
    NEURO_DESCRIPTIONS,
    SPLACHNOLOGY_DESCRIPTIONS,
)
from src.schemas.users_schemas import UsersGet, UsersPost
from src.utils.dni_utils import DniUtils
from src.utils.constraints import should_bypass_auth
from src.utils.fernet_utils import FernetUtils
from src.utils.jwt_utils import JWTUtils
from src.utils.user_lookup_utils import UserLookupUtils


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
        dni="12345678",
        password="secret123",
    )
    fernet = FernetUtils()

    assert body.name != "Pedro Vieira"
    assert body.email != "pedro@example.com"
    assert body.nickname != "pedrov"
    assert body.dni != "12345678"
    assert body.password != "secret123"
    assert fernet.decrypt(body.name) == "Pedro Vieira"
    assert fernet.decrypt(body.email) == "pedro@example.com"
    assert fernet.decrypt(body.nickname) == "pedrov"
    assert fernet.decrypt(body.dni) == "12345678"
    assert fernet.decrypt(body.password) == "secret123"


def test_users_get_decrypts_sensitive_fields():
    fernet = FernetUtils()

    user = UsersGet(
        id=uuid4(),
        name=fernet.encrypt("Pedro Vieira"),
        email=fernet.encrypt("pedro@example.com"),
        nickname=fernet.encrypt("pedrov"),
        dni=fernet.encrypt("12345678"),
        global_role="User",
        created_at=datetime.now(),
        updated_at=None,
    )

    assert user.name == "Pedro Vieira"
    assert user.email == "pedro@example.com"
    assert user.nickname == "pedrov"
    assert user.dni == "12345678"


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


def test_dni_utils_normalize_and_validate_accepts_valid_dni():
    assert DniUtils.normalize_and_validate("12.345.678") == "12345678"


def test_dni_utils_normalize_and_validate_rejects_invalid_dni():
    try:
        DniUtils.normalize_and_validate("00000000")
    except ValueError as exc:
        assert "invalid" in str(exc).lower()
    else:
        assert False, "Expected invalid DNI error"


def test_dni_utils_normalize_and_validate_rejects_invalid_length():
    with_error = []

    for invalid_dni in ("123", "123456789"):
        try:
            DniUtils.normalize_and_validate(invalid_dni)
        except ValueError as exc:
            with_error.append(str(exc))

    assert "7 or 8 digits" in with_error[0]
    assert "7 or 8 digits" in with_error[1]


def test_user_lookup_utils_hash_email_normalizes_case_and_spaces():
    first_hash = UserLookupUtils.hash_email(" Pedro@Example.com ")
    second_hash = UserLookupUtils.hash_email("pedro@example.com")

    assert first_hash == second_hash


def test_user_lookup_utils_hash_nickname_preserves_current_case_sensitivity():
    assert UserLookupUtils.hash_nickname("pedrov") != UserLookupUtils.hash_nickname(
        "PedroV"
    )


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


def test_check_biology_sub_topic_for_biologia_celular(monkeypatch):
    expected_key = next(iter(BIOLOGIA_CELULAR_Y_MOLECULAR_DESCRIPTIONS.keys()))
    monkeypatch.setattr(
        "src.helpers.check_subtopic.random.choice", lambda seq: expected_key
    )

    subtopic, description = check_biology_sub_topic("Biologia Celular y Molecular")

    assert subtopic == expected_key
    assert description == BIOLOGIA_CELULAR_Y_MOLECULAR_DESCRIPTIONS[expected_key]


def test_check_biology_sub_topic_for_genetica(monkeypatch):
    expected_key = next(iter(GENETICA_DESCRIPTIONS.keys()))
    monkeypatch.setattr(
        "src.helpers.check_subtopic.random.choice", lambda seq: expected_key
    )

    subtopic, description = check_biology_sub_topic("Genetica")

    assert subtopic == expected_key
    assert description == GENETICA_DESCRIPTIONS[expected_key]


def test_check_biology_sub_topic_rejects_unsupported_topic():
    try:
        check_biology_sub_topic("Botanica")
    except ValueError as exc:
        assert "Unsupported biology topic" in str(exc)
    else:
        assert False, "Expected unsupported topic error"
