import asyncio
from datetime import datetime, timedelta
import smtplib
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

import src.services.ai_anatomy_service as ai_anatomy_service_module
import src.services.ai_biology_service as ai_biology_service_module
from src.models.models import Questions, Subscriptions
from src.schemas.questions_schemas import OnlyQuestionsGetSchema
from src.services.ai_anatomy_service import AIAnatomyService
from src.services.ai_biology_service import AIBiologyService
from src.services.auth_service import AuthService
from src.services.email_service import EmailService
from src.services.question_answers_service import QuestionAnswersService
from src.services.questions_service import QuestionsService
from src.services.stripe_service import StripeService
from src.services.subscription_service import SubscriptionService
from src.services.user_service import UserService
from src.utils.fernet_utils import FernetUtils
from src.utils.user_lookup_utils import UserLookupUtils
from tests.conftest import FakeAsyncSession, FakeExecuteResult


def _build_user(global_role="User"):
    fernet = FernetUtils()
    return SimpleNamespace(
        id=uuid4(),
        name=fernet.encrypt("Pedro Vieira"),
        email=fernet.encrypt("pedro@example.com"),
        email_hash=UserLookupUtils.hash_email("pedro@example.com"),
        nickname=fernet.encrypt("pedrov"),
        nickname_hash=UserLookupUtils.hash_nickname("pedrov"),
        password=fernet.encrypt("secret123"),
        global_role=global_role,
    )


def _build_question(question_id=None, institution_id=None):
    return Questions(
        id=question_id or uuid4(),
        institution_id=institution_id or uuid4(),
        topic="Neuroanatomy",
        subtopic="cerebelo",
        subtopic_description="estrutura do cerebelo",
        diversity_mode="relationship",
        question="Qual estrutura pertence ao cerebelo?",
        answer_a="Lobo anterior",
        answer_b="Mesencéfalo",
        answer_c="Bulbo",
        answer_d="Tálamo",
        explanation_a="A alternativa A é correta.",
        explanation_b="A alternativa B é incorreta.",
        explanation_c="A alternativa C é incorreta.",
        explanation_d="A alternativa D é incorreta.",
        answer_e=None,
        explanation_e=None,
        correct_answer="A",
        created_at=datetime.now(),
        updated_at=None,
    )


def test_auth_service_user_has_active_subscription_true():
    db = FakeAsyncSession(
        execute_results=[FakeExecuteResult(scalars_items=[SimpleNamespace(id=uuid4())])]
    )

    response = asyncio.run(AuthService.user_has_active_subscription(uuid4(), db))

    assert response is True


def test_auth_service_user_has_active_subscription_false():
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[])])

    response = asyncio.run(AuthService.user_has_active_subscription(uuid4(), db))

    assert response is False


def test_auth_service_login_returns_admin_user():
    admin_user = _build_user(global_role="Admin")
    db = FakeAsyncSession(
        execute_results=[FakeExecuteResult(scalars_items=[admin_user])]
    )

    response = asyncio.run(AuthService.login("pedrov", "secret123", db))

    assert response is admin_user


def test_auth_service_login_returns_uba_user_institution(monkeypatch):
    base_user = _build_user()
    expected_institution = SimpleNamespace(id=uuid4())
    expected_user_institution = SimpleNamespace(
        user=SimpleNamespace(id=base_user.id),
        institution_id=expected_institution.id,
        profile=SimpleNamespace(name="basic_uba_user"),
    )
    db = FakeAsyncSession(
        execute_results=[FakeExecuteResult(scalars_items=[base_user])]
    )

    async def _get_uba_institution(_db):
        return expected_institution

    async def _read_user_institutions(user_id, institution_id, _db):
        assert user_id == base_user.id
        assert institution_id == expected_institution.id
        return expected_user_institution

    monkeypatch.setattr(
        "src.services.auth_service.InstitutionsService.get_uba_institution",
        _get_uba_institution,
    )
    monkeypatch.setattr(
        "src.services.auth_service.UserInstitutionService.read_user_institutions",
        _read_user_institutions,
    )

    response = asyncio.run(AuthService.login("pedrov", "secret123", db))

    assert response is expected_user_institution


def test_auth_service_login_returns_base_user_when_no_uba_membership(monkeypatch):
    base_user = _build_user()
    db = FakeAsyncSession(
        execute_results=[FakeExecuteResult(scalars_items=[base_user])]
    )

    async def _get_uba_institution(_db):
        return SimpleNamespace(id=uuid4())

    async def _read_user_institutions(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "src.services.auth_service.InstitutionsService.get_uba_institution",
        _get_uba_institution,
    )
    monkeypatch.setattr(
        "src.services.auth_service.UserInstitutionService.read_user_institutions",
        _read_user_institutions,
    )

    response = asyncio.run(AuthService.login("pedrov", "secret123", db))

    assert response is base_user


def test_auth_service_login_rejects_invalid_credentials():
    user = _build_user()
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[user])])

    try:
        asyncio.run(AuthService.login("pedrov", "wrong-password", db))
    except ValueError as exc:
        assert str(exc) == "Invalid nickname or password"
    else:
        assert False, "Expected invalid credentials error"


def test_auth_service_request_password_reset_returns_token():
    user = _build_user()
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[user])])

    token = asyncio.run(AuthService.request_password_reset("pedro@example.com", db))
    payload = AuthService.reset_password.__globals__["JWTUtils"].decode_jwt(token)

    assert payload["sub"] == str(user.id)
    assert payload["purpose"] == "password_reset"


def test_auth_service_request_password_reset_returns_none_for_unknown_email():
    user = _build_user()
    db = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(scalars_items=[]),
            FakeExecuteResult(scalars_items=[user]),
        ]
    )

    token = asyncio.run(AuthService.request_password_reset("missing@example.com", db))

    assert token is None


def test_auth_service_login_fallbacks_to_legacy_user_and_backfills_hashes(monkeypatch):
    fernet = FernetUtils()
    legacy_user = SimpleNamespace(
        id=uuid4(),
        name=fernet.encrypt("Pedro Vieira"),
        email=fernet.encrypt("pedro@example.com"),
        email_hash=None,
        nickname=fernet.encrypt("pedrov"),
        nickname_hash=None,
        password=fernet.encrypt("secret123"),
        global_role="Admin",
    )
    db = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(scalars_items=[]),
            FakeExecuteResult(scalars_items=[legacy_user]),
        ]
    )

    response = asyncio.run(AuthService.login("pedrov", "secret123", db))

    assert response is legacy_user
    assert legacy_user.email_hash == UserLookupUtils.hash_email("pedro@example.com")
    assert legacy_user.nickname_hash == UserLookupUtils.hash_nickname("pedrov")
    assert db.committed is True


def test_auth_service_request_password_reset_fallbacks_to_legacy_user(monkeypatch):
    fernet = FernetUtils()
    legacy_user = SimpleNamespace(
        id=uuid4(),
        name=fernet.encrypt("Pedro Vieira"),
        email=fernet.encrypt("pedro@example.com"),
        email_hash=None,
        nickname=fernet.encrypt("pedrov"),
        nickname_hash=None,
        password=fernet.encrypt("secret123"),
        global_role="User",
    )
    db = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(scalars_items=[]),
            FakeExecuteResult(scalars_items=[legacy_user]),
        ]
    )

    token = asyncio.run(AuthService.request_password_reset("pedro@example.com", db))
    payload = AuthService.reset_password.__globals__["JWTUtils"].decode_jwt(token)

    assert payload["sub"] == str(legacy_user.id)
    assert legacy_user.email_hash == UserLookupUtils.hash_email("pedro@example.com")
    assert legacy_user.nickname_hash == UserLookupUtils.hash_nickname("pedrov")
    assert db.committed is True


def test_auth_service_reset_password_updates_encrypted_password():
    user = _build_user()
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[user])])
    token = AuthService.reset_password.__globals__["JWTUtils"].encode_jwt(
        {"id": str(user.id), "sub": str(user.id), "purpose": "password_reset"}
    )

    asyncio.run(AuthService.reset_password(token, "NovaSenha123!", db))

    assert AuthService.reset_password.__globals__["fernet_utils"].decrypt(
        user.password
    ) == ("NovaSenha123!")
    assert user.updated_at is not None
    assert db.committed is True


def test_auth_service_reset_password_rejects_invalid_purpose():
    user = _build_user()
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[user])])
    token = AuthService.reset_password.__globals__["JWTUtils"].encode_jwt(
        {"id": str(user.id), "sub": str(user.id), "purpose": "login"}
    )

    with pytest.raises(ValueError) as exc:
        asyncio.run(AuthService.reset_password(token, "NovaSenha123!", db))

    assert str(exc.value) == "Invalid password reset token"


def test_auth_service_reset_password_rejects_weak_password():
    user = _build_user()
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[user])])
    token = AuthService.reset_password.__globals__["JWTUtils"].encode_jwt(
        {"id": str(user.id), "sub": str(user.id), "purpose": "password_reset"}
    )

    with pytest.raises(ValueError) as exc:
        asyncio.run(AuthService.reset_password(token, "weak", db))

    assert "Password must be at least 8 characters long" in str(exc.value)


def test_email_service_builds_password_reset_url(monkeypatch):
    monkeypatch.setattr(
        "src.services.email_service.settings",
        SimpleNamespace(
            PASSWORD_RESET_URL="https://app.example.com/reset-password",
            SMTP_FROM_EMAIL="noreply@example.com",
            SMTP_FROM_NAME="UBA Questionary",
            PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES=30,
        ),
    )

    message = EmailService._build_password_reset_message(
        "pedro@example.com",
        "reset-token",
    )

    assert message.get_content_type() == "text/html"
    assert "link de redefinicao de senha" in message.get_content()
    assert 'href="https://app.example.com/reset-password?token=reset-token"' in (
        message.get_content()
    )


def test_email_service_uses_plain_token_when_reset_url_missing(monkeypatch):
    monkeypatch.setattr(
        "src.services.email_service.settings",
        SimpleNamespace(
            PASSWORD_RESET_URL=None,
            SMTP_FROM_EMAIL="noreply@example.com",
            SMTP_FROM_NAME="UBA Questionary",
            PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES=30,
        ),
    )

    message = EmailService._build_password_reset_message(
        "pedro@example.com",
        "reset-token",
    )

    assert message.get_content_type() == "text/html"
    assert 'href="reset-token"' in message.get_content()
    assert "link de redefinicao de senha" in message.get_content()


def test_email_service_build_password_reset_message_requires_from_email(monkeypatch):
    monkeypatch.setattr(
        "src.services.email_service.settings",
        SimpleNamespace(
            PASSWORD_RESET_URL="https://app.example.com/reset-password",
            SMTP_FROM_EMAIL=None,
            SMTP_FROM_NAME="UBA Questionary",
            PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES=30,
        ),
    )

    with pytest.raises(RuntimeError) as exc:
        EmailService._build_password_reset_message(
            "pedro@example.com",
            "reset-token",
        )

    assert str(exc.value) == "SMTP_FROM_EMAIL must be configured when SMTP is enabled."


def test_email_service_sends_message_with_tls_and_login(monkeypatch):
    events = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            events.append(("connect", host, port, timeout))

        def ehlo(self):
            events.append("ehlo")

        def starttls(self):
            events.append("starttls")

        def login(self, username, password):
            events.append(("login", username, password))

        def send_message(self, message):
            events.append(("send_message", message["To"], message["Subject"]))

        def quit(self):
            events.append("quit")

    monkeypatch.setattr("src.services.email_service.smtplib.SMTP", FakeSMTP)
    monkeypatch.setattr(
        "src.services.email_service.settings",
        SimpleNamespace(
            SMTP_ENABLED=True,
            SMTP_HOST="smtp.example.com",
            SMTP_PORT=587,
            SMTP_USERNAME="noreply@example.com",
            SMTP_PASSWORD="secret",
            SMTP_USE_TLS=True,
            SMTP_USE_SSL=False,
            SMTP_FROM_EMAIL="noreply@example.com",
            SMTP_FROM_NAME="UBA Questionary",
            PASSWORD_RESET_URL="https://app.example.com/reset-password",
            PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES=30,
        ),
    )

    EmailService.send_password_reset_email("pedro@example.com", "reset-token")

    assert ("connect", "smtp.example.com", 587, 30) in events
    assert "starttls" in events
    assert ("login", "noreply@example.com", "secret") in events
    assert ("send_message", "pedro@example.com", "Redefinicao de senha") in events
    assert "quit" in events


def test_email_service_returns_without_delivery_when_disabled(monkeypatch):
    monkeypatch.setattr(
        "src.services.email_service.settings",
        SimpleNamespace(SMTP_ENABLED=False),
    )

    EmailService.send_password_reset_email("pedro@example.com", "reset-token")


def test_email_service_requires_host_and_from_email_when_enabled(monkeypatch):
    monkeypatch.setattr(
        "src.services.email_service.settings",
        SimpleNamespace(
            SMTP_ENABLED=True,
            SMTP_HOST=None,
            SMTP_FROM_EMAIL=None,
        ),
    )

    with pytest.raises(RuntimeError) as exc:
        EmailService.send_password_reset_email("pedro@example.com", "reset-token")

    assert str(exc.value) == (
        "SMTP is enabled but SMTP_HOST/SMTP_FROM_EMAIL are not fully configured."
    )


def test_email_service_requires_credentials_for_gmail_smtp(monkeypatch):
    monkeypatch.setattr(
        "src.services.email_service.settings",
        SimpleNamespace(
            SMTP_ENABLED=True,
            SMTP_HOST="smtp.gmail.com",
            SMTP_PORT=587,
            SMTP_USERNAME=None,
            SMTP_PASSWORD=None,
            SMTP_USE_TLS=True,
            SMTP_USE_SSL=False,
            SMTP_FROM_EMAIL="noreply@example.com",
            SMTP_FROM_NAME="UBA Questionary",
        ),
    )

    with pytest.raises(RuntimeError) as exc:
        EmailService.send_password_reset_email("pedro@example.com", "reset-token")

    assert str(exc.value) == (
        "SMTP_USERNAME/SMTP_PASSWORD must be configured when using smtp.gmail.com."
    )


def test_email_service_requires_16_char_gmail_app_password(monkeypatch):
    monkeypatch.setattr(
        "src.services.email_service.settings",
        SimpleNamespace(
            SMTP_ENABLED=True,
            SMTP_HOST="smtp.gmail.com",
            SMTP_PORT=587,
            SMTP_USERNAME="support@example.com",
            SMTP_PASSWORD="short-password",
            SMTP_USE_TLS=True,
            SMTP_USE_SSL=False,
            SMTP_FROM_EMAIL="support@example.com",
            SMTP_FROM_NAME="Soporte Axios",
        ),
    )

    with pytest.raises(RuntimeError) as exc:
        EmailService.send_password_reset_email("pedro@example.com", "reset-token")

    assert str(exc.value) == (
        "SMTP_PASSWORD for smtp.gmail.com must be a 16-character Google app password."
    )


def test_email_service_normalizes_quoted_gmail_credentials(monkeypatch):
    events = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            events.append(("connect", host, port, timeout))

        def ehlo(self):
            events.append("ehlo")

        def starttls(self):
            events.append("starttls")

        def login(self, username, password):
            events.append(("login", username, password))

        def send_message(self, message):
            events.append(("send_message", message["To"], message["Subject"]))

        def quit(self):
            events.append("quit")

    monkeypatch.setattr("src.services.email_service.smtplib.SMTP", FakeSMTP)
    monkeypatch.setattr(
        "src.services.email_service.settings",
        SimpleNamespace(
            SMTP_ENABLED=True,
            SMTP_HOST='"smtp.gmail.com"',
            SMTP_PORT=587,
            SMTP_USERNAME='"support@example.com"',
            SMTP_PASSWORD='"abcd efgh ijkl mnop"',
            SMTP_USE_TLS=True,
            SMTP_USE_SSL=False,
            SMTP_FROM_EMAIL='"support@example.com"',
            SMTP_FROM_NAME="Soporte Axios",
            PASSWORD_RESET_URL="https://app.example.com/reset-password",
            PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES=30,
        ),
    )

    EmailService.send_password_reset_email("pedro@example.com", "reset-token")

    assert ("connect", "smtp.gmail.com", 587, 30) in events
    assert (
        "login",
        "support@example.com",
        "abcdefghijklmnop",
    ) in events
    assert ("send_message", "pedro@example.com", "Redefinicao de senha") in events
    assert "quit" in events


def test_email_service_wraps_delivery_errors(monkeypatch):
    events = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            events.append(("connect", host, port, timeout))

        def ehlo(self):
            events.append("ehlo")

        def starttls(self):
            events.append("starttls")

        def login(self, username, password):
            events.append(("login", username, password))

        def send_message(self, message):
            events.append(("send_message", message["To"]))
            raise ValueError("smtp failure")

        def quit(self):
            events.append("quit")

    monkeypatch.setattr("src.services.email_service.smtplib.SMTP", FakeSMTP)
    monkeypatch.setattr(
        "src.services.email_service.settings",
        SimpleNamespace(
            SMTP_ENABLED=True,
            SMTP_HOST="smtp.example.com",
            SMTP_PORT=587,
            SMTP_USERNAME="noreply@example.com",
            SMTP_PASSWORD="secret",
            SMTP_USE_TLS=True,
            SMTP_USE_SSL=False,
            SMTP_FROM_EMAIL="noreply@example.com",
            SMTP_FROM_NAME="UBA Questionary",
            PASSWORD_RESET_URL="https://app.example.com/reset-password",
            PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES=30,
        ),
    )

    with pytest.raises(RuntimeError) as exc:
        EmailService.send_password_reset_email("pedro@example.com", "reset-token")

    assert str(exc.value) == "Unable to send password reset email."
    assert ("send_message", "pedro@example.com") in events
    assert "quit" in events


def test_email_service_ignores_disconnected_quit_after_delivery_error(monkeypatch):
    events = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            events.append(("connect", host, port, timeout))

        def ehlo(self):
            events.append("ehlo")

        def starttls(self):
            events.append("starttls")

        def login(self, username, password):
            events.append(("login", username, password))

        def send_message(self, message):
            events.append(("send_message", message["To"]))
            raise smtplib.SMTPSenderRefused(550, b"relay denied", "from@example.com")

        def quit(self):
            events.append("quit")
            raise smtplib.SMTPServerDisconnected("please run connect() first")

    monkeypatch.setattr("src.services.email_service.smtplib.SMTP", FakeSMTP)
    monkeypatch.setattr(
        "src.services.email_service.settings",
        SimpleNamespace(
            SMTP_ENABLED=True,
            SMTP_HOST="smtp.example.com",
            SMTP_PORT=587,
            SMTP_USERNAME="noreply@example.com",
            SMTP_PASSWORD="secret",
            SMTP_USE_TLS=True,
            SMTP_USE_SSL=False,
            SMTP_FROM_EMAIL="noreply@example.com",
            SMTP_FROM_NAME="UBA Questionary",
            PASSWORD_RESET_URL="https://app.example.com/reset-password",
            PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES=30,
        ),
    )

    with pytest.raises(RuntimeError) as exc:
        EmailService.send_password_reset_email("pedro@example.com", "reset-token")

    assert str(exc.value) == "Unable to send password reset email."
    assert ("send_message", "pedro@example.com") in events
    assert "quit" in events


def test_user_service_check_user_existance_rejects_invalid_uuid():
    try:
        asyncio.run(UserService.check_user_existance("not-a-uuid", FakeAsyncSession()))
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "Incorrect Id format"
    else:
        assert False, "Expected invalid UUID error"


def test_user_service_check_user_existance_returns_true():
    db = FakeAsyncSession(
        execute_results=[FakeExecuteResult(scalars_items=[SimpleNamespace(id=uuid4())])]
    )

    response = asyncio.run(UserService.check_user_existance(str(uuid4()), db))

    assert response is True


def test_user_service_get_user_checkout_contact_decrypts_user_data():
    fernet = FernetUtils()
    user = SimpleNamespace(
        id=uuid4(),
        email=fernet.encrypt("pedro@example.com"),
        name=fernet.encrypt("Pedro Vieira"),
    )
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[user])])

    response = asyncio.run(UserService.get_user_checkout_contact(str(user.id), db))

    assert response == {
        "id": user.id,
        "email": "pedro@example.com",
    }


def test_user_service_parse_user_id_handles_uuid_and_invalid_value():
    user_id = uuid4()

    assert UserService._parse_user_id(user_id) == user_id

    with pytest.raises(HTTPException) as exc:
        UserService._parse_user_id("invalid-uuid")

    assert exc.value.status_code == 400
    assert exc.value.detail == "Incorrect Id format"


def test_user_service_get_user_checkout_contact_handles_missing_user_and_placeholder_cbu():
    fernet = FernetUtils()
    pending_user = SimpleNamespace(
        id=uuid4(),
        email=fernet.encrypt("pedro@example.com"),
        cbu=fernet.encrypt("0000000000000000000000"),
    )
    db_missing = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[])])
    db_pending = FakeAsyncSession(
        execute_results=[FakeExecuteResult(scalars_items=[pending_user])]
    )

    missing = asyncio.run(UserService.get_user_checkout_contact(str(uuid4()), db_missing))
    pending = asyncio.run(
        UserService.get_user_checkout_contact(str(pending_user.id), db_pending)
    )

    assert missing is None
    assert pending == {
        "id": pending_user.id,
        "email": "pedro@example.com",
        "has_pending_cbu": True,
    }


def test_question_answers_service_maps_latest_answers():
    question = _build_question()
    answered_at = datetime.now() - timedelta(hours=1)
    updated_at = datetime.now()
    user_id = uuid4()
    db = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(rows=[(question, "B", user_id, answered_at, updated_at)])
        ]
    )

    response = asyncio.run(
        QuestionAnswersService.get_questions_with_latest_user_answers(user_id, db)
    )

    assert len(response["data"]) == 1
    payload = response["data"][0]
    assert payload.id == question.id
    assert payload.user_answer == "B"
    assert payload.user_id == user_id
    assert payload.answered_at == answered_at


def test_questions_service_get_last_three_questions_returns_mapped_items():
    question = _build_question()
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[question])])

    response = asyncio.run(
        QuestionsService.get_last_three_questions("Neuroanatomy", "cerebelo", db)
    )

    assert response == [OnlyQuestionsGetSchema(question=question.question)]


def test_questions_service_get_last_three_questions_returns_empty_list():
    db = FakeAsyncSession(execute_results=[FakeExecuteResult(scalars_items=[])])

    response = asyncio.run(
        QuestionsService.get_last_three_questions("Neuroanatomy", "cerebelo", db)
    )

    assert response == []


def test_subscription_service_parse_uuid_accepts_string(sample_ids):
    parsed = SubscriptionService._parse_uuid(str(sample_ids.user_id), "user_id")

    assert parsed == sample_ids.user_id


def test_subscription_service_parse_uuid_rejects_invalid_value():
    try:
        SubscriptionService._parse_uuid("invalid", "institution_id")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "Invalid institution_id format."
    else:
        assert False, "Expected invalid UUID error"


def test_subscription_service_sync_generation_cycle_resets_counter():
    next_cycle = datetime.now() + timedelta(days=30)
    subscription = SimpleNamespace(
        current_period_end=next_cycle,
        questions_generation_cycle_end=datetime.now(),
        questions_generated_in_cycle=9,
        updated_at=None,
    )

    SubscriptionService._sync_generation_cycle(subscription)

    assert subscription.questions_generated_in_cycle == 0
    assert subscription.questions_generation_cycle_end == next_cycle
    assert subscription.updated_at is not None


def test_subscription_service_sync_generation_cycle_keeps_counter_without_period_end():
    subscription = SimpleNamespace(
        current_period_end=None,
        questions_generation_cycle_end=None,
        questions_generated_in_cycle=9,
        updated_at=None,
    )

    SubscriptionService._sync_generation_cycle(subscription)

    assert subscription.questions_generated_in_cycle == 9
    assert subscription.updated_at is None


def test_subscription_service_get_generation_context_rejects_missing_profile(
    sample_ids,
):
    db = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(scalars_items=[SimpleNamespace(profile=None)])
        ]
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            SubscriptionService._get_generation_context(
                sample_ids.user_id,
                sample_ids.institution_id,
                db,
                lock_subscription=False,
            )
        )

    assert exc.value.status_code == 403
    assert (
        exc.value.detail == "User does not have a valid profile for this institution."
    )


def test_subscription_service_get_generation_context_rejects_missing_subscription(
    sample_ids,
):
    membership = SimpleNamespace(profile=SimpleNamespace(questions_create_limit=5))
    db = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(scalars_items=[membership]),
            FakeExecuteResult(scalars_items=[]),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            SubscriptionService._get_generation_context(
                sample_ids.user_id,
                sample_ids.institution_id,
                db,
                lock_subscription=True,
            )
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Active question package required."


def test_subscription_service_get_generation_context_returns_membership_and_subscription(
    sample_ids,
):
    membership = SimpleNamespace(profile=SimpleNamespace(questions_create_limit=5))
    subscription = SimpleNamespace(status="active")
    db = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(scalars_items=[membership]),
            FakeExecuteResult(scalars_items=[subscription]),
        ]
    )

    response_membership, response_subscription = asyncio.run(
        SubscriptionService._get_generation_context(
            sample_ids.user_id,
            sample_ids.institution_id,
            db,
            lock_subscription=False,
        )
    )

    assert response_membership is membership
    assert response_subscription is subscription


def test_subscription_service_validate_generation_limit_rejects_when_reaching_limit():
    with pytest.raises(HTTPException) as exc:
        SubscriptionService._validate_generation_limit(
            SimpleNamespace(questions_generated_in_cycle=5),
            5,
        )

    assert exc.value.status_code == 403
    assert (
        exc.value.detail == "Question package exhausted. Buy a new package to continue."
    )


def test_subscription_service_build_usage_summary_handles_empty_subscription():
    response = SubscriptionService._build_usage_summary(None, 5)

    assert response == {
        "questions_used": 0,
        "questions_limit": 5,
        "questions_remaining": 5,
        "cycle_end": None,
        "subscription_status": None,
    }


def test_subscription_service_validate_question_generation_availability(monkeypatch):
    cycle_end = datetime.now() + timedelta(days=30)
    subscription = SimpleNamespace(
        current_period_end=cycle_end,
        questions_generation_cycle_end=cycle_end,
        questions_generated_in_cycle=2,
        status="active",
    )
    user_institution = SimpleNamespace(
        profile=SimpleNamespace(questions_create_limit=5)
    )

    async def _context(*args, **kwargs):
        return user_institution, subscription

    monkeypatch.setattr(
        SubscriptionService, "_get_generation_context", staticmethod(_context)
    )

    response = asyncio.run(
        SubscriptionService.validate_question_generation_availability(
            uuid4(), uuid4(), FakeAsyncSession()
        )
    )

    assert response["questions_used"] == 2
    assert response["questions_limit"] == 5
    assert response["questions_remaining"] == 3
    assert response["subscription_status"] == "active"


def test_subscription_service_create_question_and_consume_quota(
    sample_ids, monkeypatch
):
    cycle_end = datetime.now() + timedelta(days=30)
    subscription = Subscriptions(
        id=sample_ids.subscription_id,
        user_id=sample_ids.user_id,
        stripe_subscription_id="sub_123",
        status="active",
        price_id="price_test",
        current_period_end=cycle_end,
        questions_generated_in_cycle=1,
        questions_generation_cycle_end=cycle_end,
        created_at=datetime.now(),
        updated_at=None,
    )
    user_institution = SimpleNamespace(
        profile=SimpleNamespace(questions_create_limit=5)
    )
    db = FakeAsyncSession()

    async def _context(*args, **kwargs):
        return user_institution, subscription

    monkeypatch.setattr(
        SubscriptionService, "_get_generation_context", staticmethod(_context)
    )

    payload = {
        "id": uuid4(),
        "institution_id": sample_ids.institution_id,
        "topic": "Neuroanatomy",
        "subtopic": "cerebelo",
        "subtopic_description": "estrutura do cerebelo",
        "diversity_mode": "relationship",
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
        "answer_e": None,
        "explanation_e": None,
    }

    question, usage = asyncio.run(
        SubscriptionService.create_question_and_consume_quota(
            sample_ids.user_id,
            sample_ids.institution_id,
            payload,
            db,
        )
    )

    assert question.question == payload["question"]
    assert subscription.questions_generated_in_cycle == 2
    assert db.committed is True
    assert len(db.added) == 1
    assert usage["questions_used"] == 2
    assert usage["questions_remaining"] == 3


def test_subscription_service_create_question_and_consume_quota_cancels_exhausted_package(
    sample_ids, monkeypatch
):
    subscription = Subscriptions(
        id=sample_ids.subscription_id,
        user_id=sample_ids.user_id,
        stripe_subscription_id="cs_123",
        status="active",
        price_id="price_test",
        current_period_end=None,
        questions_generated_in_cycle=4,
        questions_generation_cycle_end=None,
        created_at=datetime.now(),
        updated_at=None,
    )
    user_institution = SimpleNamespace(
        profile=SimpleNamespace(questions_create_limit=5)
    )
    db = FakeAsyncSession()
    calls = []

    async def _context(*args, **kwargs):
        return user_institution, subscription

    async def _sync_access(*args, **kwargs):
        calls.append("sync")
        return "deleted"

    monkeypatch.setattr(
        SubscriptionService, "_get_generation_context", staticmethod(_context)
    )
    monkeypatch.setattr(
        "src.services.subscription_service.StripeService._sync_user_access_for_user",
        _sync_access,
    )

    _, usage = asyncio.run(
        SubscriptionService.create_question_and_consume_quota(
            sample_ids.user_id,
            sample_ids.institution_id,
            {
                "id": uuid4(),
                "institution_id": sample_ids.institution_id,
                "topic": "Neuroanatomy",
                "subtopic": "cerebelo",
                "subtopic_description": "estrutura do cerebelo",
                "diversity_mode": "relationship",
                "question": "Pergunta",
                "answer_a": "A",
                "answer_b": "B",
                "answer_c": "C",
                "answer_d": "D",
                "explanation_a": "EA",
                "explanation_b": "EB",
                "explanation_c": "EC",
                "explanation_d": "ED",
                "correct_answer": "A",
                "answer_e": None,
                "explanation_e": None,
            },
            db,
        )
    )

    assert subscription.status == "canceled"
    assert usage["questions_remaining"] == 0
    assert usage["subscription_status"] == "canceled"
    assert calls == ["sync"]


def test_subscription_service_get_question_generation_usage_without_institution(
    sample_ids,
):
    cycle_end = datetime.now() + timedelta(days=30)
    subscription = SimpleNamespace(
        questions_generated_in_cycle=2,
        questions_generation_cycle_end=cycle_end,
        current_period_end=cycle_end,
        status="active",
    )
    db = FakeAsyncSession(
        execute_results=[FakeExecuteResult(scalars_items=[subscription])]
    )

    response = asyncio.run(
        SubscriptionService.get_question_generation_usage(sample_ids.user_id, None, db)
    )

    assert response["questions_used"] == 2
    assert response["questions_limit"] is None
    assert response["subscription_status"] == "active"


def test_subscription_service_get_question_generation_usage_ignores_invalid_institution(
    sample_ids,
):
    cycle_end = datetime.now() + timedelta(days=30)
    subscription = SimpleNamespace(
        questions_generated_in_cycle=2,
        questions_generation_cycle_end=cycle_end,
        current_period_end=cycle_end,
        status="active",
    )
    db = FakeAsyncSession(
        execute_results=[FakeExecuteResult(scalars_items=[subscription])]
    )

    response = asyncio.run(
        SubscriptionService.get_question_generation_usage(
            sample_ids.user_id, "invalid", db
        )
    )

    assert response["questions_limit"] is None
    assert response["questions_remaining"] is None


def test_subscription_service_get_question_generation_usage_with_profile_limit(
    sample_ids,
):
    cycle_end = datetime.now() + timedelta(days=30)
    subscription = SimpleNamespace(
        questions_generated_in_cycle=2,
        questions_generation_cycle_end=cycle_end,
        current_period_end=cycle_end,
        status="active",
        created_at=datetime.now(),
    )
    membership = SimpleNamespace(profile=SimpleNamespace(questions_create_limit=5))
    db = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(scalars_items=[subscription]),
            FakeExecuteResult(scalars_items=[membership]),
        ]
    )

    response = asyncio.run(
        SubscriptionService.get_question_generation_usage(
            sample_ids.user_id,
            sample_ids.institution_id,
            db,
        )
    )

    assert response["questions_limit"] == 5
    assert response["questions_remaining"] == 3


def test_subscription_service_get_question_generation_usage_falls_back_to_latest_subscription(
    sample_ids,
):
    cycle_end = datetime.now() + timedelta(days=30)
    canceled_subscription = SimpleNamespace(
        questions_generated_in_cycle=4,
        questions_generation_cycle_end=cycle_end,
        current_period_end=cycle_end,
        status="canceled",
        created_at=datetime.now(),
    )
    db = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(scalars_items=[]),
            FakeExecuteResult(scalars_items=[canceled_subscription]),
        ]
    )

    response = asyncio.run(
        SubscriptionService.get_question_generation_usage(sample_ids.user_id, None, db)
    )

    assert response["questions_used"] == 4
    assert response["questions_limit"] is None
    assert response["subscription_status"] == "canceled"


def test_subscription_service_handle_exhausted_subscription_ignores_missing_limit(
    sample_ids, monkeypatch
):
    subscription = SimpleNamespace(
        questions_generated_in_cycle=10,
        status="active",
        updated_at=None,
    )
    calls = []

    async def _sync_access(*args, **kwargs):
        calls.append("sync")
        return "deleted"

    monkeypatch.setattr(
        "src.services.subscription_service.StripeService._sync_user_access_for_user",
        _sync_access,
    )

    asyncio.run(
        SubscriptionService._handle_exhausted_subscription(
            subscription=subscription,
            questions_limit=None,
            user_id=sample_ids.user_id,
            db=FakeAsyncSession(),
        )
    )

    assert subscription.status == "active"
    assert calls == []


def test_subscription_service_create_question_rolls_back_on_commit_error(
    sample_ids, monkeypatch
):
    cycle_end = datetime.now() + timedelta(days=30)
    subscription = Subscriptions(
        id=sample_ids.subscription_id,
        user_id=sample_ids.user_id,
        stripe_subscription_id="sub_123",
        status="active",
        price_id="price_test",
        current_period_end=cycle_end,
        questions_generated_in_cycle=0,
        questions_generation_cycle_end=cycle_end,
        created_at=datetime.now(),
        updated_at=None,
    )
    user_institution = SimpleNamespace(
        profile=SimpleNamespace(questions_create_limit=5)
    )
    db = FakeAsyncSession(commit_error=RuntimeError("commit failed"))

    async def _context(*args, **kwargs):
        return user_institution, subscription

    monkeypatch.setattr(
        SubscriptionService, "_get_generation_context", staticmethod(_context)
    )

    try:
        asyncio.run(
            SubscriptionService.create_question_and_consume_quota(
                sample_ids.user_id,
                sample_ids.institution_id,
                {
                    "id": uuid4(),
                    "institution_id": sample_ids.institution_id,
                    "topic": "Neuroanatomy",
                    "subtopic": "cerebelo",
                    "subtopic_description": "estrutura do cerebelo",
                    "diversity_mode": "relationship",
                    "question": "Pergunta",
                    "answer_a": "A",
                    "answer_b": "B",
                    "answer_c": "C",
                    "answer_d": "D",
                    "explanation_a": "EA",
                    "explanation_b": "EB",
                    "explanation_c": "EC",
                    "explanation_d": "ED",
                    "correct_answer": "A",
                    "answer_e": None,
                    "explanation_e": None,
                },
                db,
            )
        )
    except RuntimeError as exc:
        assert str(exc) == "commit failed"
    else:
        assert False, "Expected commit error"

    assert db.rolled_back is True


def test_stripe_service_extract_user_id_from_supported_locations():
    direct = StripeService._extract_user_id_from_metadata(
        {"metadata": {"user_id": "direct-user"}}
    )
    nested = StripeService._extract_user_id_from_metadata(
        {"subscription_details": {"metadata": {"user_id": "nested-user"}}}
    )
    parent_nested = StripeService._extract_user_id_from_metadata(
        {"parent": {"subscription_details": {"metadata": {"user_id": "parent-user"}}}}
    )

    assert direct == "direct-user"
    assert nested == "nested-user"
    assert parent_nested == "parent-user"


def test_stripe_service_extract_user_id_returns_none_for_invalid_payload():
    assert StripeService._extract_user_id_from_metadata("invalid") is None


def test_stripe_service_extract_price_id_from_supported_locations():
    assert (
        StripeService._extract_price_id({"metadata": {"price_id": "price_meta"}})
        == "price_meta"
    )
    assert (
        StripeService._extract_price_id(
            {"items": {"data": [{"price": {"id": "price_items"}}]}}
        )
        == "price_items"
    )
    assert (
        StripeService._extract_price_id(
            {"lines": {"data": [{"price": {"id": "price_lines"}}]}}
        )
        == "price_lines"
    )


def test_stripe_service_extract_price_id_from_subscription_details_and_invalid_payload():
    assert (
        StripeService._extract_price_id(
            {"subscription_details": {"metadata": {"price_id": "price_subscription"}}}
        )
        == "price_subscription"
    )
    assert StripeService._extract_price_id("invalid") is None


def test_stripe_service_normalize_subscription_status():
    assert StripeService._normalize_subscription_status("active") == "active"
    assert StripeService._normalize_subscription_status("paused") == "failed_payment"
    assert StripeService._normalize_subscription_status("unknown") == "incomplete"


def test_stripe_service_generate_payment_checkout_builds_expected_payload(monkeypatch):
    captured = {}

    def _create(payload):
        captured["payload"] = payload
        return SimpleNamespace(url="https://checkout.stripe.test")

    monkeypatch.setattr(
        "src.services.stripe_service.stripe_client.v1.checkout.sessions.create",
        _create,
    )
    monkeypatch.setattr(
        "src.services.stripe_service.StripeService._resolve_promotion_code_id",
        staticmethod(lambda coupon_code: None),
    )

    response = StripeService.generate_payment_checkout(
        uuid4(), customer_email="pedro@example.com"
    )

    assert response == {"url_session": "https://checkout.stripe.test"}
    assert captured["payload"]["mode"] == "payment"
    assert captured["payload"]["adaptive_pricing"] == {"enabled": True}
    assert captured["payload"]["allow_promotion_codes"] is True
    assert "billing_address_collection" not in captured["payload"]
    assert captured["payload"]["customer_creation"] == "always"
    assert captured["payload"]["customer_email"] == "pedro@example.com"
    assert captured["payload"]["invoice_creation"] == {"enabled": True}
    assert captured["payload"]["locale"] == "es"
    assert captured["payload"]["line_items"] == [{"price": "price_test", "quantity": 1}]
    assert captured["payload"]["payment_intent_data"]["receipt_email"] == (
        "pedro@example.com"
    )
    assert (
        captured["payload"]["payment_method_options"]["card"]["request_three_d_secure"]
        == "automatic"
    )


def test_stripe_service_generate_payment_checkout_applies_coupon_code(monkeypatch):
    captured = {}

    def _create(payload):
        captured["payload"] = payload
        return SimpleNamespace(url="https://checkout.stripe.test")

    monkeypatch.setattr(
        "src.services.stripe_service.stripe_client.v1.checkout.sessions.create",
        _create,
    )
    monkeypatch.setattr(
        "src.services.stripe_service.StripeService._resolve_promotion_code_id",
        staticmethod(lambda coupon_code: "promo_123"),
    )

    response = StripeService.generate_payment_checkout(
        uuid4(),
        customer_email="pedro@example.com",
        coupon_code="PROMO-UBA",
    )

    assert response == {"url_session": "https://checkout.stripe.test"}
    assert captured["payload"]["discounts"] == [{"promotion_code": "promo_123"}]
    assert captured["payload"]["allow_promotion_codes"] is False


def test_stripe_service_resolve_promotion_code_id_rejects_missing_code(monkeypatch):
    monkeypatch.setattr(
        "src.services.stripe_service.stripe_client.v1.promotion_codes.list",
        lambda payload: {"data": []},
    )

    try:
        StripeService._resolve_promotion_code_id("PROMO-UBA")
    except ValueError as exc:
        assert str(exc) == "Coupon code is invalid or inactive"
    else:
        assert False, "Expected invalid coupon error"


def test_stripe_service_resolve_promotion_code_id_returns_none_for_blank_code():
    assert StripeService._resolve_promotion_code_id("   ") is None


def test_stripe_service_resolve_promotion_code_id_returns_matching_id(monkeypatch):
    monkeypatch.setattr(
        "src.services.stripe_service.stripe_client.v1.promotion_codes.list",
        lambda payload: {"data": [{"id": "promo_123"}]},
    )

    assert StripeService._resolve_promotion_code_id("PROMO-UBA") == "promo_123"


def test_stripe_service_normalize_payload_handles_to_dict_recursive_and_items_fallback():
    class ToDictRecursiveOnly:
        def to_dict_recursive(self):
            return {"nested": {"value": 1}}

    class ItemsRaisingTypeError:
        def items(self):
            raise TypeError("unsupported items")

    normalized_recursive = StripeService._normalize_stripe_payload(
        ToDictRecursiveOnly()
    )
    fallback_payload = ItemsRaisingTypeError()
    normalized_fallback = StripeService._normalize_stripe_payload(fallback_payload)

    assert normalized_recursive == {"nested": {"value": 1}}
    assert normalized_fallback is fallback_payload


def test_stripe_service_get_uba_context_returns_institution_and_profile():
    institution = SimpleNamespace(id=uuid4(), name="UBA")
    profile = SimpleNamespace(id=uuid4(), name="basic_uba_user")
    db = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(scalars_items=[institution]),
            FakeExecuteResult(scalars_items=[profile]),
        ]
    )

    response = asyncio.run(StripeService._get_uba_context(db))

    assert response == (institution, profile)


def test_stripe_service_get_subscription_by_stripe_id_handles_missing_id():
    response = asyncio.run(
        StripeService._get_subscription_by_stripe_id(FakeAsyncSession(), None)
    )

    assert response is None


def test_stripe_service_get_subscription_by_stripe_id_returns_subscription():
    subscription = SimpleNamespace(stripe_subscription_id="sub_123")
    db = FakeAsyncSession(
        execute_results=[FakeExecuteResult(scalars_items=[subscription])]
    )

    response = asyncio.run(StripeService._get_subscription_by_stripe_id(db, "sub_123"))

    assert response is subscription


def test_stripe_service_get_user_institution_returns_membership():
    membership = SimpleNamespace(user_id=uuid4())
    db = FakeAsyncSession(
        execute_results=[FakeExecuteResult(scalars_items=[membership])]
    )

    response = asyncio.run(StripeService._get_user_institution(db, uuid4(), uuid4()))

    assert response is membership


def test_stripe_service_upsert_subscription_updates_existing_period_change(monkeypatch):
    current_period_end = datetime.now()
    next_period_end = current_period_end + timedelta(days=30)
    existing = SimpleNamespace(
        user_id=uuid4(),
        status="active",
        price_id="old_price",
        stripe_customer_id="cus_old",
        current_period_end=current_period_end,
        questions_generated_in_cycle=3,
        questions_generation_cycle_end=current_period_end,
        updated_at=None,
    )

    async def _existing(*args, **kwargs):
        return existing

    monkeypatch.setattr(
        StripeService, "_get_subscription_by_stripe_id", staticmethod(_existing)
    )

    subscription, operation = asyncio.run(
        StripeService._upsert_subscription(
            FakeAsyncSession(),
            uuid4(),
            "sub_123",
            "active",
            "new_price",
            stripe_customer_id="cus_new",
            current_period_end=next_period_end,
        )
    )

    assert subscription is existing
    assert operation == "updated"
    assert existing.questions_generated_in_cycle == 0
    assert existing.questions_generation_cycle_end == next_period_end
    assert existing.price_id == "new_price"


def test_stripe_service_upsert_subscription_updates_cycle_end_when_missing(monkeypatch):
    current_period_end = datetime.now() + timedelta(days=30)
    existing = SimpleNamespace(
        user_id=uuid4(),
        status="active",
        price_id="old_price",
        stripe_customer_id="cus_old",
        current_period_end=current_period_end,
        questions_generated_in_cycle=1,
        questions_generation_cycle_end=None,
        updated_at=None,
    )

    async def _existing(*args, **kwargs):
        return existing

    monkeypatch.setattr(
        StripeService, "_get_subscription_by_stripe_id", staticmethod(_existing)
    )

    subscription, operation = asyncio.run(
        StripeService._upsert_subscription(
            FakeAsyncSession(),
            uuid4(),
            "sub_123",
            "active",
            None,
            stripe_customer_id=None,
            current_period_end=None,
        )
    )

    assert subscription is existing
    assert operation == "updated"
    assert existing.questions_generation_cycle_end == current_period_end


def test_stripe_service_upsert_subscription_creates_new(sample_ids):
    db = FakeAsyncSession()

    subscription, operation = asyncio.run(
        StripeService._upsert_subscription(
            db,
            sample_ids.user_id,
            "sub_123",
            "active",
            "price_test",
            stripe_customer_id="cus_123",
            current_period_end=datetime.now() + timedelta(days=30),
        )
    )

    assert operation == "created"
    assert len(db.added) == 1
    assert subscription.stripe_subscription_id == "sub_123"


def test_stripe_service_grant_user_access_updates_existing_membership(monkeypatch):
    membership = SimpleNamespace(profile_id=uuid4(), updated_at=None)
    new_profile_id = uuid4()

    async def _membership(*args, **kwargs):
        return membership

    monkeypatch.setattr(
        StripeService, "_get_user_institution", staticmethod(_membership)
    )

    response = asyncio.run(
        StripeService._grant_user_access(
            FakeAsyncSession(), uuid4(), uuid4(), new_profile_id
        )
    )

    assert response == "updated"
    assert membership.profile_id == new_profile_id


def test_stripe_service_grant_user_access_keeps_existing_membership(monkeypatch):
    profile_id = uuid4()
    membership = SimpleNamespace(profile_id=profile_id, updated_at=None)

    async def _membership(*args, **kwargs):
        return membership

    monkeypatch.setattr(
        StripeService, "_get_user_institution", staticmethod(_membership)
    )

    response = asyncio.run(
        StripeService._grant_user_access(
            FakeAsyncSession(), uuid4(), uuid4(), profile_id
        )
    )

    assert response == "unchanged"


def test_stripe_service_grant_user_access_creates_membership(monkeypatch):
    db = FakeAsyncSession()

    async def _membership(*args, **kwargs):
        return None

    monkeypatch.setattr(
        StripeService, "_get_user_institution", staticmethod(_membership)
    )

    response = asyncio.run(
        StripeService._grant_user_access(db, uuid4(), uuid4(), uuid4())
    )

    assert response == "created"
    assert len(db.added) == 1


def test_stripe_service_revoke_user_access_handles_missing_membership(monkeypatch):
    async def _membership(*args, **kwargs):
        return None

    monkeypatch.setattr(
        StripeService, "_get_user_institution", staticmethod(_membership)
    )

    response = asyncio.run(
        StripeService._revoke_user_access(FakeAsyncSession(), uuid4(), uuid4())
    )

    assert response == "unchanged"


def test_stripe_service_revoke_user_access_deletes_membership(monkeypatch):
    membership = SimpleNamespace(id=uuid4())
    db = FakeAsyncSession()

    async def _membership(*args, **kwargs):
        return membership

    monkeypatch.setattr(
        StripeService, "_get_user_institution", staticmethod(_membership)
    )

    response = asyncio.run(StripeService._revoke_user_access(db, uuid4(), uuid4()))

    assert response == "deleted"
    assert db.deleted == [membership]


def test_stripe_service_user_has_active_subscription(monkeypatch):
    db = FakeAsyncSession(
        execute_results=[FakeExecuteResult(scalars_items=[SimpleNamespace(id=uuid4())])]
    )

    response = asyncio.run(StripeService._user_has_active_subscription(db, uuid4()))

    assert response is True


def test_stripe_service_sync_user_access_requires_seed_data(monkeypatch):
    async def _context(*args, **kwargs):
        return None, None

    monkeypatch.setattr(StripeService, "_get_uba_context", staticmethod(_context))

    with pytest.raises(ValueError) as exc:
        asyncio.run(
            StripeService._sync_user_access(FakeAsyncSession(), uuid4(), "active")
        )

    assert "seed data for UBA institution/profile" in str(exc.value)


def test_stripe_service_sync_user_access_grants_active_access(monkeypatch):
    institution = SimpleNamespace(id=uuid4())
    profile = SimpleNamespace(id=uuid4())

    async def _context(*args, **kwargs):
        return institution, profile

    async def _grant(*args, **kwargs):
        return "created"

    monkeypatch.setattr(StripeService, "_get_uba_context", staticmethod(_context))
    monkeypatch.setattr(StripeService, "_grant_user_access", staticmethod(_grant))

    response = asyncio.run(
        StripeService._sync_user_access(FakeAsyncSession(), uuid4(), "active")
    )

    assert response == "created"


def test_stripe_service_sync_user_access_revokes_inactive_access(monkeypatch):
    institution = SimpleNamespace(id=uuid4())
    profile = SimpleNamespace(id=uuid4())

    async def _context(*args, **kwargs):
        return institution, profile

    async def _revoke(*args, **kwargs):
        return "deleted"

    monkeypatch.setattr(StripeService, "_get_uba_context", staticmethod(_context))
    monkeypatch.setattr(StripeService, "_revoke_user_access", staticmethod(_revoke))

    response = asyncio.run(
        StripeService._sync_user_access(FakeAsyncSession(), uuid4(), "failed_payment")
    )

    assert response == "deleted"


def test_stripe_service_sync_user_access_for_user_grants_when_active_subscription_exists(
    monkeypatch,
):
    async def _has_active(*args, **kwargs):
        return True

    async def _sync(*args, **kwargs):
        return "created"

    monkeypatch.setattr(
        StripeService, "_user_has_active_subscription", staticmethod(_has_active)
    )
    monkeypatch.setattr(StripeService, "_sync_user_access", staticmethod(_sync))

    response = asyncio.run(
        StripeService._sync_user_access_for_user(FakeAsyncSession(), uuid4())
    )

    assert response == "created"


def test_stripe_service_sync_checkout_session_purchase_ignores_missing_user(
    monkeypatch,
):
    existing = None

    async def _existing(*args, **kwargs):
        return existing

    monkeypatch.setattr(
        StripeService, "_get_subscription_by_stripe_id", staticmethod(_existing)
    )

    response = asyncio.run(
        StripeService._sync_checkout_session_purchase(
            {
                "type": "checkout.session.completed",
                "data": {"object": {"id": "cs_123"}},
            },
            FakeAsyncSession(),
        )
    )

    assert response == {
        "status": "ignored",
        "reason": "user_id_not_found",
        "event": "checkout.session.completed",
    }


def test_stripe_service_sync_checkout_session_purchase_processes_payload(monkeypatch):
    subscription = SimpleNamespace(stripe_subscription_id="cs_123", status="active")
    db = FakeAsyncSession()

    async def _existing(*args, **kwargs):
        return SimpleNamespace(user_id=uuid4())

    async def _upsert_subscription(**kwargs):
        return subscription, "updated"

    async def _sync_access(*args, **kwargs):
        return "created"

    monkeypatch.setattr(
        StripeService, "_get_subscription_by_stripe_id", staticmethod(_existing)
    )
    monkeypatch.setattr(
        StripeService, "_upsert_subscription", staticmethod(_upsert_subscription)
    )
    monkeypatch.setattr(
        StripeService, "_sync_user_access_for_user", staticmethod(_sync_access)
    )

    response = asyncio.run(
        StripeService._sync_checkout_session_purchase(
            {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_123",
                        "payment_status": "paid",
                        "metadata": {"user_id": str(uuid4()), "price_id": "price_test"},
                        "customer": "cus_123",
                    }
                },
            },
            db,
            normalized_status=None,
        )
    )

    assert response["status"] == "processed"
    assert response["subscription_action"] == "updated"
    assert response["access_action"] == "created"


def test_stripe_service_checkout_session_completed_ignores_missing_user():
    response = asyncio.run(
        StripeService.checkout_session_completed(
            {"type": "checkout.session.completed", "data": {"object": {}}},
            FakeAsyncSession(),
        )
    )

    assert response == {
        "status": "ignored",
        "reason": "checkout_session_not_found",
        "event": "checkout.session.completed",
    }


def test_stripe_service_checkout_session_completed_updates_existing_subscription(
    monkeypatch,
):
    existing = SimpleNamespace(
        status="active",
        stripe_customer_id=None,
        price_id=None,
        updated_at=None,
    )

    async def _existing(*args, **kwargs):
        return existing

    async def _sync_access(*args, **kwargs):
        return "updated"

    monkeypatch.setattr(
        StripeService, "_get_subscription_by_stripe_id", staticmethod(_existing)
    )
    monkeypatch.setattr(
        StripeService, "_sync_user_access_for_user", staticmethod(_sync_access)
    )

    response = asyncio.run(
        StripeService.checkout_session_completed(
            {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_123",
                        "client_reference_id": str(uuid4()),
                        "customer": "cus_123",
                        "payment_status": "paid",
                        "metadata": {"price_id": "price_test", "user_id": str(uuid4())},
                    }
                },
            },
            FakeAsyncSession(),
        )
    )

    assert response["status"] == "processed"
    assert response["subscription_action"] == "updated"
    assert response["access_action"] == "updated"


def test_stripe_service_checkout_session_completed_creates_subscription(monkeypatch):
    async def _existing(*args, **kwargs):
        return None

    async def _upsert_subscription(**kwargs):
        return (
            SimpleNamespace(stripe_subscription_id="cs_123", status="active"),
            "created",
        )

    async def _sync_access(*args, **kwargs):
        return "created"

    monkeypatch.setattr(
        StripeService, "_get_subscription_by_stripe_id", staticmethod(_existing)
    )
    monkeypatch.setattr(
        StripeService, "_upsert_subscription", staticmethod(_upsert_subscription)
    )
    monkeypatch.setattr(
        StripeService, "_sync_user_access_for_user", staticmethod(_sync_access)
    )

    response = asyncio.run(
        StripeService.checkout_session_completed(
            {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_123",
                        "client_reference_id": str(uuid4()),
                        "customer": "cus_123",
                        "payment_status": "paid",
                    }
                },
            },
            FakeAsyncSession(),
        )
    )

    assert response["subscription_action"] == "created"
    assert response["subscription_status"] == "active"


def test_stripe_service_checkout_session_async_wrappers_delegate(monkeypatch):
    calls = []

    async def _sync(data, db, normalized_status=None):
        calls.append(normalized_status)
        return {"normalized_status": normalized_status}

    monkeypatch.setattr(
        StripeService, "_sync_checkout_session_purchase", staticmethod(_sync)
    )

    succeeded = asyncio.run(
        StripeService.checkout_session_async_payment_succeeded({}, FakeAsyncSession())
    )
    failed = asyncio.run(
        StripeService.checkout_session_async_payment_failed({}, FakeAsyncSession())
    )

    assert succeeded == {"normalized_status": "active"}
    assert failed == {"normalized_status": "failed_payment"}
    assert calls == ["active", "failed_payment"]


@pytest.mark.parametrize(
    ("handler_name", "event_name", "category", "action_required"),
    [
        ("charge_succeeded", "charge.succeeded", "charge_succeeded", False),
        ("charge_failed", "charge.failed", "charge_failed", True),
        ("charge_updated", "charge.updated", "charge_updated", False),
        (
            "charge_dispute_created",
            "charge.dispute.created",
            "charge_dispute_created",
            True,
        ),
        (
            "charge_dispute_closed",
            "charge.dispute.closed",
            "charge_dispute_closed",
            False,
        ),
        (
            "radar_early_fraud_warning_created",
            "radar.early_fraud_warning.created",
            "early_fraud_warning",
            True,
        ),
    ],
)
def test_stripe_service_monitoring_handlers_return_structured_payload(
    handler_name, event_name, category, action_required
):
    handler = getattr(StripeService, handler_name)

    response = asyncio.run(
        handler(
            {
                "type": event_name,
                "data": {
                    "object": {
                        "id": "obj_123",
                        "object": "charge",
                        "payment_intent": "pi_123",
                        "metadata": {
                            "user_id": str(uuid4()),
                            "price_id": "price_test",
                        },
                        "billing_details": {"email": "pedro@example.com"},
                        "amount": 3000000,
                        "currency": "ars",
                        "status": "succeeded",
                    }
                },
            },
            FakeAsyncSession(),
        )
    )

    assert response["status"] == "processed"
    assert response["event"] == event_name
    assert response["monitoring_category"] == category
    assert response["action_required"] is action_required
    assert response["customer_email"] == "pedro@example.com"
    assert response["amount"] == 3000000


def test_stripe_service_unsupported_subscription_and_invoice_events_are_ignored():
    events = [
        ("customer.subscription.created", StripeService.customer_subscription_created),
        ("customer.subscription.updated", StripeService.customer_subscription_updated),
        ("customer.subscription.paused", StripeService.customer_subscription_paused),
        ("customer.subscription.resumed", StripeService.customer_subscription_resumed),
        ("customer.subscription.deleted", StripeService.customer_subscription_deleted),
        ("invoice.paid", StripeService.invoice_paid),
        ("invoice.payment_succeeded", StripeService.invoice_payment_succeeded),
        ("invoice.payment_failed", StripeService.invoice_payment_failed),
    ]

    for event_name, handler in events:
        response = asyncio.run(
            handler({"type": event_name, "data": {"object": {}}}, FakeAsyncSession())
        )

        assert response == {
            "status": "ignored",
            "reason": "unsupported_event",
            "event": event_name,
        }


def test_ai_anatomy_service_generate_response_formats_prompt(monkeypatch):
    expected_response = SimpleNamespace(id="response-123")
    captured = {}

    def _create(*, model, input):
        captured["model"] = model
        captured["input"] = input
        return expected_response

    monkeypatch.setattr(ai_anatomy_service_module.client.responses, "create", _create)

    response = asyncio.run(
        AIAnatomyService.generate_response(
            parameter="Neuroanatomy",
            subtopic="cerebelo",
            subtopic_description="estrutura do cerebelo",
            diversity_mode="relationship",
            correct_letter="B",
            recent_questions=[SimpleNamespace(question="Pergunta antiga")],
        )
    )

    assert response is expected_response
    assert captured["model"] == "gpt-5.4-mini"
    assert "Neuroanatomy" in captured["input"]
    assert "cerebelo" in captured["input"]
    assert "Pergunta antiga" in captured["input"]
    assert "relationship" in captured["input"]


def test_ai_anatomy_service_generate_response_handles_empty_recent_questions(
    monkeypatch,
):
    captured = {}

    def _create(*, model, input):
        captured["input"] = input
        return SimpleNamespace(id="response-123")

    monkeypatch.setattr(ai_anatomy_service_module.client.responses, "create", _create)

    asyncio.run(
        AIAnatomyService.generate_response(
            parameter="Neuroanatomy",
            subtopic="cerebelo",
            subtopic_description="estrutura do cerebelo",
            diversity_mode="relationship",
            correct_letter="B",
            recent_questions=[],
        )
    )

    assert "There are no recent questions to avoid repetition." in captured["input"]


def test_ai_biology_service_generate_response_formats_prompt(monkeypatch):
    expected_response = SimpleNamespace(id="response-123")
    captured = {}

    def _create(*, model, input):
        captured["model"] = model
        captured["input"] = input
        return expected_response

    monkeypatch.setattr(ai_biology_service_module.client.responses, "create", _create)

    response = asyncio.run(
        AIBiologyService.generate_response(
            parameter="Genetica",
            subtopic="herencia_mitocondrial",
            subtopic_description="transmision y heteroplasmia",
            diversity_mode="mechanism",
            correct_letter="B",
            recent_questions=[SimpleNamespace(question="Pergunta antiga")],
        )
    )

    assert response is expected_response
    assert captured["model"] == "gpt-5.4-mini"
    assert "Genetica" in captured["input"]
    assert "herencia_mitocondrial" in captured["input"]
    assert "Pergunta antiga" in captured["input"]
    assert "mechanism" in captured["input"]


def test_ai_biology_service_generate_response_handles_empty_recent_questions(
    monkeypatch,
):
    captured = {}

    def _create(*, model, input):
        captured["input"] = input
        return SimpleNamespace(id="response-123")

    monkeypatch.setattr(ai_biology_service_module.client.responses, "create", _create)

    asyncio.run(
        AIBiologyService.generate_response(
            parameter="Genetica",
            subtopic="herencia_mitocondrial",
            subtopic_description="transmision y heteroplasmia",
            diversity_mode="mechanism",
            correct_letter="B",
            recent_questions=[],
        )
    )

    assert "There are no recent questions to avoid repetition." in captured["input"]


def test_stripe_service_parse_uuid_returns_uuid(sample_ids):
    assert StripeService._parse_uuid(str(sample_ids.user_id)) == sample_ids.user_id
    assert isinstance(StripeService._parse_uuid(str(sample_ids.user_id)), UUID)


def test_stripe_service_parse_uuid_returns_uuid_instance(sample_ids):
    assert StripeService._parse_uuid(sample_ids.user_id) == sample_ids.user_id


def test_stripe_service_parse_uuid_returns_none_for_invalid_value():
    assert StripeService._parse_uuid("invalid") is None


def test_stripe_service_unix_to_datetime_handles_none():
    assert StripeService._unix_to_datetime(None) is None


def test_stripe_service_unix_to_datetime_converts_timestamp():
    assert StripeService._unix_to_datetime(1) == datetime(1970, 1, 1, 0, 0, 1)
