import asyncio
import json
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException

from src.controllers.ai_anatomy_controller import AIAnatomyController
from src.controllers.auth_controller import AuthController
from src.controllers.stripe_controller import StripeController
from src.controllers.users_controller import UsersController
from src.schemas.users_schemas import UsersPost
from src.utils.fernet_utils import FernetUtils
from tests.conftest import FakeAsyncSession


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
    fernet = FernetUtils()
    db = FakeAsyncSession()
    existing_user = SimpleNamespace(
        nickname=fernet.encrypt("pedrov"),
        email=fernet.encrypt("other@example.com"),
    )
    body = UsersPost(
        name="Pedro Vieira",
        email="pedro@example.com",
        nickname="pedrov",
        password="Secret123!",
    )

    async def _read(*args, **kwargs):
        return [existing_user], 1

    monkeypatch.setattr(
        UsersController.create_user.__globals__["generic_user_service"],
        "read",
        _read,
    )

    try:
        asyncio.run(UsersController.create_user(body, db))
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "Nickname or Email already exists"
    else:
        assert False, "Expected duplicate user error"


def test_users_controller_create_user_persists_unique_user(monkeypatch):
    body = UsersPost(
        name="Pedro Vieira",
        email="pedro@example.com",
        nickname="pedrov",
        password="Secret123!",
    )
    created_user = SimpleNamespace(id=uuid4())

    async def _read(*args, **kwargs):
        return [], 0

    async def _create(*args, **kwargs):
        return created_user

    monkeypatch.setattr(
        UsersController.create_user.__globals__["generic_user_service"],
        "read",
        _read,
    )
    monkeypatch.setattr(
        UsersController.create_user.__globals__["generic_user_service"],
        "create",
        _create,
    )

    response = asyncio.run(UsersController.create_user(body, FakeAsyncSession()))

    assert response == {"data": created_user}


def test_users_controller_create_user_rejects_weak_password():
    body = UsersPost(
        name="Pedro Vieira",
        email="pedro@example.com",
        nickname="pedrov",
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


def test_stripe_controller_generate_payment_checkout_returns_url(monkeypatch):
    monkeypatch.setattr(
        "src.controllers.stripe_controller.UserService.get_user_checkout_contact",
        lambda *args, **kwargs: asyncio.sleep(
            0, result={"id": uuid4(), "email": "pedro@example.com"}
        ),
    )
    captured = {}

    def _generate_checkout(user_id, customer_email=None):
        captured["user_id"] = user_id
        captured["customer_email"] = customer_email
        return {"url_session": "https://checkout.stripe.test"}

    monkeypatch.setattr(
        "src.controllers.stripe_controller.StripeService.generate_payment_checkout",
        staticmethod(_generate_checkout),
    )

    response = asyncio.run(
        StripeController.generate_payment_checkout(str(uuid4()), FakeAsyncSession())
    )

    assert response == {"url_session": "https://checkout.stripe.test"}
    assert captured["customer_email"] == "pedro@example.com"


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
